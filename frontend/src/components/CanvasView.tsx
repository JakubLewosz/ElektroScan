import { Check, Maximize2, Minus, Plus, X } from 'lucide-react';
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import type { PointerEvent, WheelEvent } from 'react';

import { ContextMenu, type CanvasContextMenuState } from './ContextMenu';
import type {
  BoxStatus,
  CanvasMode,
  DetectionBox,
  PreviewResponse,
  Rect,
  SlideshowMode,
} from '../types';

interface DragState {
  pointerId: number;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
}

interface PanState {
  pointerId: number;
  startX: number;
  startY: number;
  scrollLeft: number;
  scrollTop: number;
}

export interface CanvasViewHandle {
  showBox: (box: DetectionBox) => void;
}

interface CanvasViewProps {
  preview: PreviewResponse | null;
  visibleBoxes: DetectionBox[];
  boxes: DetectionBox[];
  boxStatuses: Record<string, BoxStatus>;
  symbolNumberMap: Record<string, string>;
  excludedZones: Rect[];
  focusedBoxId: string | null;
  mode: CanvasMode;
  slideshow: SlideshowMode | null;
  slideshowBox: DetectionBox | null;
  symbolNames: string[];
  onAddExcludedZone: (rect: Rect) => void;
  onAddManualBox: (rect: Rect) => void;
  onFocusBox: (boxId: string) => void;
  onCopyBoxLog: (box: DetectionBox) => void | Promise<void>;
  onMarkBox: (boxId: string, status: BoxStatus) => void;
  onMarkCurrentSlideshowBox: (status: BoxStatus) => void;
  onChangeBoxType: (boxId: string, symbolName: string) => void;
  onCloseSlideshow: () => void;
}

const LOW_CONFIDENCE_THRESHOLD = 0.6;
const MIN_ZOOM = 0.05;
const MAX_ZOOM = 6;

function clampZoom(value: number): number {
  return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, value));
}

function normalizeRect(rect: DragState): Rect {
  const x = Math.round(Math.min(rect.startX, rect.currentX));
  const y = Math.round(Math.min(rect.startY, rect.currentY));
  const width = Math.round(Math.abs(rect.currentX - rect.startX));
  const height = Math.round(Math.abs(rect.currentY - rect.startY));
  return { x, y, width, height };
}

function statusOf(statuses: Record<string, BoxStatus>, boxId: string): BoxStatus {
  return statuses[boxId] ?? 'pending';
}

export const CanvasView = forwardRef<CanvasViewHandle, CanvasViewProps>(function CanvasView(
  {
    preview,
    visibleBoxes,
    boxes,
    boxStatuses,
    symbolNumberMap,
    excludedZones,
    focusedBoxId,
    mode,
    slideshow,
    slideshowBox,
    symbolNames,
    onAddExcludedZone,
    onAddManualBox,
    onFocusBox,
    onCopyBoxLog,
    onMarkBox,
    onMarkCurrentSlideshowBox,
    onChangeBoxType,
    onCloseSlideshow,
  },
  ref,
) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const [zoom, setZoom] = useState(0.35);
  const [drag, setDrag] = useState<DragState | null>(null);
  const [pan, setPan] = useState<PanState | null>(null);
  const [contextMenu, setContextMenu] = useState<CanvasContextMenuState | null>(null);

  function centerBoxInView(box: DetectionBox, behavior: ScrollBehavior = 'smooth') {
    const container = scrollRef.current;
    if (!container) {
      return;
    }
    container.scrollTo({
      left: Math.max(0, (box.x + box.width / 2) * zoom - container.clientWidth / 2),
      top: Math.max(0, (box.y + box.height / 2) * zoom - container.clientHeight / 2),
      behavior,
    });
  }

  useImperativeHandle(
    ref,
    () => ({
      showBox: (box) => {
        onFocusBox(box.id);
        centerBoxInView(box);
      },
    }),
    [onFocusBox, zoom],
  );

  useEffect(() => {
    if (slideshow) {
      setZoom((current) => Math.max(current, 2.5));
    }
  }, [slideshow]);

  useEffect(() => {
    if (!slideshowBox) {
      return;
    }
    requestAnimationFrame(() => {
      centerBoxInView(slideshowBox);
      onFocusBox(slideshowBox.id);
    });
  }, [onFocusBox, slideshowBox, zoom]);

  function getPoint(event: PointerEvent<HTMLDivElement>): { x: number; y: number } | null {
    const target = canvasRef.current;
    if (!target || !preview) {
      return null;
    }
    const rect = target.getBoundingClientRect();
    const x = Math.max(0, Math.min(preview.pageSize.width, (event.clientX - rect.left) / zoom));
    const y = Math.max(0, Math.min(preview.pageSize.height, (event.clientY - rect.top) / zoom));
    return { x, y };
  }

  function setZoomAroundPoint(nextZoom: number, clientX: number, clientY: number) {
    const container = scrollRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) {
      setZoom(nextZoom);
      return;
    }

    const canvasRect = canvas.getBoundingClientRect();
    const anchorX = (clientX - canvasRect.left) / zoom;
    const anchorY = (clientY - canvasRect.top) / zoom;

    setZoom(nextZoom);
    requestAnimationFrame(() => {
      const containerRect = container.getBoundingClientRect();
      container.scrollLeft = anchorX * nextZoom - (clientX - containerRect.left);
      container.scrollTop = anchorY * nextZoom - (clientY - containerRect.top);
    });
  }

  function changeZoom(multiplier: number) {
    const container = scrollRef.current;
    const nextZoom = clampZoom(zoom * multiplier);
    if (!container) {
      setZoom(nextZoom);
      return;
    }
    const rect = container.getBoundingClientRect();
    setZoomAroundPoint(nextZoom, rect.left + rect.width / 2, rect.top + rect.height / 2);
  }

  function fitPreviewToView() {
    const container = scrollRef.current;
    if (!container || !preview) {
      return;
    }
    const widthRatio = (container.clientWidth - 32) / preview.pageSize.width;
    const heightRatio = (container.clientHeight - 32) / preview.pageSize.height;
    setZoom(clampZoom(Math.min(widthRatio, heightRatio)));
    requestAnimationFrame(() => container.scrollTo({ left: 0, top: 0 }));
  }

  function handleCanvasWheel(event: WheelEvent) {
    if (slideshow) {
      return;
    }
    if (!event.ctrlKey && !event.metaKey && !event.altKey) {
      return;
    }
    event.preventDefault();
    setZoomAroundPoint(clampZoom(zoom * (event.deltaY > 0 ? 0.9 : 1.1)), event.clientX, event.clientY);
  }

  function startCanvasPan(event: PointerEvent<HTMLDivElement>) {
    const container = scrollRef.current;
    if (!container) {
      return;
    }
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    setContextMenu(null);
    setPan({
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      scrollLeft: container.scrollLeft,
      scrollTop: container.scrollTop,
    });
  }

  function handleCanvasPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (slideshow) {
      return;
    }
    if (mode === 'idle' || event.button === 1) {
      if (event.button !== 0 && event.button !== 1) {
        return;
      }
      startCanvasPan(event);
      return;
    }
    if (event.button !== 0) {
      return;
    }
    const point = getPoint(event);
    if (!point) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    setDrag({ pointerId: event.pointerId, startX: point.x, startY: point.y, currentX: point.x, currentY: point.y });
  }

  function handleCanvasPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (pan?.pointerId === event.pointerId) {
      const container = scrollRef.current;
      if (!container) {
        return;
      }
      event.preventDefault();
      container.scrollLeft = pan.scrollLeft - (event.clientX - pan.startX);
      container.scrollTop = pan.scrollTop - (event.clientY - pan.startY);
      return;
    }

    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }
    const point = getPoint(event);
    if (!point) {
      return;
    }
    setDrag((current) => (current ? { ...current, currentX: point.x, currentY: point.y } : current));
  }

  function handleCanvasPointerUp(event: PointerEvent<HTMLDivElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (pan?.pointerId === event.pointerId) {
      setPan(null);
      return;
    }
    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }
    const rect = normalizeRect(drag);
    setDrag(null);
    if (rect.width < 5 || rect.height < 5) {
      return;
    }
    if (mode === 'zone') {
      onAddExcludedZone(rect);
    }
    if (mode === 'manual') {
      onAddManualBox(rect);
    }
  }

  function handleCanvasPointerCancel(event: PointerEvent<HTMLDivElement>) {
    if (pan?.pointerId === event.pointerId) {
      setPan(null);
    }
    if (drag?.pointerId === event.pointerId) {
      setDrag(null);
    }
  }

  const currentDragRect = drag ? normalizeRect(drag) : null;
  const canvasCursor = slideshow ? 'cursor-default' : pan ? 'cursor-grabbing' : mode === 'idle' ? 'cursor-grab' : 'cursor-crosshair';

  return (
    <section className="relative min-h-[70vh] overflow-hidden bg-[#0f1013] xl:min-h-0">
      {preview ? (
        <div ref={scrollRef} data-testid="canvas-scroll" className="absolute inset-0 overflow-auto" onWheel={handleCanvasWheel}>
          <div
            ref={canvasRef}
            data-testid="canvas-surface"
            className={`relative touch-none ${canvasCursor}`}
            style={{ width: preview.pageSize.width * zoom, height: preview.pageSize.height * zoom }}
            onPointerDown={handleCanvasPointerDown}
            onPointerMove={handleCanvasPointerMove}
            onPointerUp={handleCanvasPointerUp}
            onPointerCancel={handleCanvasPointerCancel}
          >
            <img
              src={preview.previewImage}
              alt={`Podgląd ${preview.fileName}`}
              draggable={false}
              className="pointer-events-none absolute inset-0 select-none"
              style={{ width: '100%', height: '100%' }}
            />

            {excludedZones.map((zone, index) => (
              <div
                key={`${zone.x}_${zone.y}_${index}`}
                className="pointer-events-none absolute border border-red-400/80 bg-red-500/10"
                style={{ left: zone.x * zoom, top: zone.y * zoom, width: zone.width * zoom, height: zone.height * zoom }}
              />
            ))}

            {visibleBoxes.map((box) => {
              const currentStatus = statusOf(boxStatuses, box.id);
              const isFocused = focusedBoxId === box.id;
              const isCurrentSlide = slideshowBox?.id === box.id;
              const symbolNumber = symbolNumberMap[box.symbolName];
              return (
                <div
                  key={box.id}
                  data-testid="canvas-detection-box"
                  title="Kliknij, aby skopiować log boxa"
                  className={[
                    'absolute cursor-pointer border-2',
                    box.verificationScore < LOW_CONFIDENCE_THRESHOLD ? 'border-dashed' : 'border-solid',
                    currentStatus === 'confirmed' ? 'outline outline-2 outline-green-400' : '',
                    isFocused || isCurrentSlide ? 'z-20 animate-pulse outline outline-4 outline-white' : 'z-10',
                  ].join(' ')}
                  style={{ left: box.x * zoom, top: box.y * zoom, width: box.width * zoom, height: box.height * zoom, borderColor: box.color }}
                  onClick={(event) => {
                    event.stopPropagation();
                    onFocusBox(box.id);
                    void onCopyBoxLog(box);
                  }}
                  onPointerDown={(event) => event.stopPropagation()}
                  onContextMenu={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    setContextMenu({ boxId: box.id, x: event.clientX, y: event.clientY });
                  }}
                >
                  {symbolNumber && (
                    <span
                      data-testid="canvas-symbol-number"
                      className="pointer-events-none absolute -left-3 -top-3 grid h-6 min-w-6 place-items-center rounded border bg-black px-1 text-xs font-bold text-white shadow-xl ring-2 ring-white"
                      style={{ borderColor: box.color }}
                    >
                      {symbolNumber}
                    </span>
                  )}
                  {box.verificationScore < LOW_CONFIDENCE_THRESHOLD && (
                    <span className="absolute -right-2 -top-2 rounded bg-yellow-400 px-1 text-[10px] font-bold text-black">!</span>
                  )}
                </div>
              );
            })}

            {currentDragRect && (
              <div
                className="pointer-events-none absolute border border-app-strong bg-orange-500/10"
                style={{
                  left: currentDragRect.x * zoom,
                  top: currentDragRect.y * zoom,
                  width: currentDragRect.width * zoom,
                  height: currentDragRect.height * zoom,
                }}
              />
            )}
          </div>
        </div>
      ) : (
        <div className="absolute inset-0 grid place-items-center">
          <div className="text-center">
            <div className="mx-auto h-14 w-14 rounded border border-dashed border-app-accent/60" />
            <p className="mt-4 text-sm text-zinc-400">Obszar podglądu planu</p>
          </div>
        </div>
      )}

      {preview && (
        <div className="absolute bottom-4 right-4 z-30 flex items-center gap-1 rounded border border-white/10 bg-black/75 p-1 shadow-xl backdrop-blur">
          <button type="button" aria-label="Pomniejsz" className="grid h-8 w-8 place-items-center rounded text-zinc-200 hover:bg-white/10" onClick={() => changeZoom(0.8)}>
            <Minus aria-hidden="true" className="h-4 w-4" />
          </button>
          <div className="min-w-14 px-2 text-center text-xs font-semibold tabular-nums text-zinc-200">{Math.round(zoom * 100)}%</div>
          <button type="button" aria-label="Powiększ" className="grid h-8 w-8 place-items-center rounded text-zinc-200 hover:bg-white/10" onClick={() => changeZoom(1.25)}>
            <Plus aria-hidden="true" className="h-4 w-4" />
          </button>
          <button type="button" aria-label="Dopasuj do widoku" className="grid h-8 w-8 place-items-center rounded text-zinc-200 hover:bg-white/10" onClick={fitPreviewToView}>
            <Maximize2 aria-hidden="true" className="h-4 w-4" />
          </button>
        </div>
      )}

      {slideshow && (
        <div
          data-testid="slideshow-overlay"
          className="absolute left-4 right-4 top-4 z-40 rounded border border-white/10 bg-black/85 p-3 text-sm text-white shadow-xl"
        >
          {slideshow.completed ? (
            <div className="flex items-center justify-between gap-3">
              <span data-testid="slideshow-complete">
                Zakończono review {slideshow.boxIds.length} boxów typu {slideshow.symbolName}. Potwierdzono: {slideshow.confirmed}, odrzucono: {slideshow.rejected}.
              </span>
              <button type="button" onClick={onCloseSlideshow} className="rounded bg-white/10 px-3 py-2">
                ESC = wyjście
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span data-testid="slideshow-counter">
                [{slideshow.symbolName}] {slideshow.currentIndex + 1}/{slideshow.boxIds.length} — verificationScore {slideshowBox?.verificationScore.toFixed(2)}{' '}
                {slideshowBox && slideshowBox.verificationScore < LOW_CONFIDENCE_THRESHOLD ? '⚠' : ''}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  data-testid="slideshow-confirm"
                  onClick={() => onMarkCurrentSlideshowBox('confirmed')}
                  className="rounded bg-green-600 px-3 py-2"
                >
                  <Check className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  data-testid="slideshow-reject"
                  onClick={() => onMarkCurrentSlideshowBox('rejected')}
                  className="rounded bg-red-600 px-3 py-2"
                >
                  <X className="h-4 w-4" />
                </button>
                <button type="button" onClick={onCloseSlideshow} className="rounded bg-white/10 px-3 py-2">
                  ESC
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {contextMenu && (
        <ContextMenu
          contextMenu={contextMenu}
          boxes={boxes}
          symbolNames={symbolNames}
          onMarkBox={onMarkBox}
          onChangeBoxType={onChangeBoxType}
          onClose={() => setContextMenu(null)}
        />
      )}
    </section>
  );
});
