from __future__ import annotations

import asyncio
import json
import shutil

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from core.config import API_PREFIX, CORS_ORIGINS, DPI
from core.detector import analyze_session
from core.legend_extractor import extract_legend_templates
from core.models import (
    AnalyzeRequest,
    ExtractLegendRequest,
    PageSize,
    PreviewResponse,
    RenameTemplateRequest,
    RenderPreviewRequest,
    RenderPreviewResponse,
    TemplateInfo,
)
from core.pdf_render import bgr_to_png_data_url, get_pdf_layers, pdf_to_bgr
from core.storage import (
    add_template_image,
    clear_templates,
    create_session_dir,
    delete_template,
    get_session_dir,
    get_source_pdf,
    list_templates,
    rename_template,
    sanitize_name,
)

app = FastAPI(title="ElektroScan API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{API_PREFIX}/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(f"{API_PREFIX}/preview", response_model=PreviewResponse)
async def preview(file: UploadFile = File(...)) -> PreviewResponse:
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status_code=400, detail="Wgraj plik PDF.")

    session_id, session_dir = create_session_dir()
    source_path = session_dir / "source.pdf"

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Wgrany PDF jest pusty.")

    source_path.write_bytes(content)

    try:
        image = pdf_to_bgr(source_path, dpi=DPI)
        preview_image = bgr_to_png_data_url(image)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Nie udalo sie wyrenderowac PDF: {exc}") from exc

    return PreviewResponse(
        sessionId=session_id,
        fileName=file.filename or "source.pdf",
        previewImage=preview_image,
        pageSize=PageSize(width=image.shape[1], height=image.shape[0]),
    )


@app.get(f"{API_PREFIX}/layers")
def layers(session_id: str = Query(...)) -> list[dict[str, bool | str]]:
    source_pdf = get_source_pdf(session_id)
    return [layer.model_dump() for layer in get_pdf_layers(source_pdf)]


@app.post(f"{API_PREFIX}/render-preview", response_model=RenderPreviewResponse)
def render_preview(request: RenderPreviewRequest, session_id: str = Query(...)) -> RenderPreviewResponse:
    source_pdf = get_source_pdf(session_id)
    image = pdf_to_bgr(source_pdf, dpi=DPI, hidden_layers=request.hiddenLayers)
    return RenderPreviewResponse(
        previewImage=bgr_to_png_data_url(image),
        pageSize=PageSize(width=image.shape[1], height=image.shape[0]),
        layers=get_pdf_layers(source_pdf, hidden_layers=request.hiddenLayers),
    )


@app.post(f"{API_PREFIX}/extract-legend", response_model=list[TemplateInfo])
def extract_legend(request: ExtractLegendRequest | None = None, session_id: str = Query(...)) -> list[TemplateInfo]:
    body = request or ExtractLegendRequest()
    source_pdf = get_source_pdf(session_id)
    try:
        return extract_legend_templates(
            session_id,
            source_pdf,
            excluded_zones=body.excludedZones,
            hidden_layers=body.hiddenLayers,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(f"{API_PREFIX}/templates", response_model=list[TemplateInfo])
def templates(session_id: str = Query(...)) -> list[TemplateInfo]:
    return list_templates(session_id)


@app.post(f"{API_PREFIX}/templates/upload", response_model=list[TemplateInfo])
async def upload_template(
    session_id: str = Query(...),
    file: UploadFile = File(...),
    displayName: str | None = Form(default=None),
) -> list[TemplateInfo]:
    content = await file.read()
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Nie mozna odczytac obrazu template'u.")

    mask = cv2.inRange(cv2.cvtColor(image, cv2.COLOR_BGR2HSV), np.array([0, 30, 50]), np.array([180, 255, 255]))
    template = np.zeros_like(image)
    template[mask > 0] = image[mask > 0]
    if cv2.countNonZero(mask) < 3:
        raise HTTPException(status_code=400, detail="Template nie zawiera kolorowych pikseli.")

    add_template_image(session_id, sanitize_name(displayName or file.filename or "manual_template"), template)
    return list_templates(session_id)


@app.patch(f"{API_PREFIX}/templates/{{template_name}}", response_model=list[TemplateInfo])
def patch_template(
    template_name: str, request: RenameTemplateRequest, session_id: str = Query(...)
) -> list[TemplateInfo]:
    rename_template(session_id, template_name, request.newName)
    return list_templates(session_id)


@app.delete(f"{API_PREFIX}/templates/{{template_name}}", response_model=list[TemplateInfo])
def remove_template(template_name: str, session_id: str = Query(...)) -> list[TemplateInfo]:
    delete_template(session_id, template_name)
    return list_templates(session_id)


@app.delete(f"{API_PREFIX}/templates", response_model=list[TemplateInfo])
def remove_templates(session_id: str = Query(...)) -> list[TemplateInfo]:
    clear_templates(session_id)
    return list_templates(session_id)


@app.post(f"{API_PREFIX}/analyze")
async def analyze(request: AnalyzeRequest, session_id: str = Query(...)) -> EventSourceResponse:
    source_pdf = get_source_pdf(session_id)

    async def event_generator():
        queue: asyncio.Queue[dict[str, str] | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def on_progress(progress):
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"event": "progress", "data": json.dumps(progress.model_dump(), ensure_ascii=False)},
            )

        def run_analysis() -> None:
            try:
                result = analyze_session(
                    session_id,
                    source_pdf,
                    excluded_zones=request.excludedZones,
                    hidden_layers=request.hiddenLayers,
                    on_progress=on_progress,
                )
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"event": "result", "data": json.dumps(result.model_dump(mode="json"), ensure_ascii=False)},
                )
            except Exception as exc:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"event": "error", "data": json.dumps({"message": str(exc)}, ensure_ascii=False)},
                )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        task = asyncio.create_task(asyncio.to_thread(run_analysis))
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            await task

    return EventSourceResponse(event_generator())


@app.post(f"{API_PREFIX}/clear")
def clear(session_id: str = Query(...)) -> dict[str, str]:
    session_dir = get_session_dir(session_id)
    shutil.rmtree(session_dir)
    return {"status": "ok"}
