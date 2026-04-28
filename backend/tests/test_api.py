from __future__ import annotations

from fastapi.testclient import TestClient

from core.storage import get_session_dir
from tests.conftest import SAMPLE_PDF, result_from_sse


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_preview_rejects_non_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/preview",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400


def test_preview_upload_creates_session(client: TestClient) -> None:
    with SAMPLE_PDF.open("rb") as handle:
        response = client.post(
            "/api/preview",
            files={"file": ("plan.pdf", handle, "application/pdf")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["fileName"] == "plan.pdf"
    assert body["previewImage"].startswith("data:image/png;base64,")
    assert body["pageSize"] == {"width": 4961, "height": 3508}

    session_id = body["sessionId"]
    session_dir = get_session_dir(session_id)
    assert (session_dir / "source.pdf").exists()

    client.post(f"/api/clear?session_id={session_id}")


def test_layers_and_legend_extraction(client: TestClient, uploaded_session: str) -> None:
    layers = client.get(f"/api/layers?session_id={uploaded_session}")
    assert layers.status_code == 200
    assert len(layers.json()) == 28

    legend = client.post(
        f"/api/extract-legend?session_id={uploaded_session}",
        json={"excludedZones": [], "hiddenLayers": []},
    )
    assert legend.status_code == 200
    templates = legend.json()
    assert len(templates) == 19
    assert all(template["imgBase64"].startswith("data:image/png;base64,") for template in templates)
    assert {template["name"] for template in templates} >= {
        "07_lacznik_schodowy",
        "08_lacznik_jednobiegunowy",
        "09_lacznik_swiecznikowy",
        "16_r_orurowanie_do_tsm",
        "18_panel_wywolania_wideodomofon",
    }
    assert max(template["height"] for template in templates) <= 90


def test_template_rename_delete_and_clear(client: TestClient, uploaded_session: str) -> None:
    legend = client.post(
        f"/api/extract-legend?session_id={uploaded_session}",
        json={"excludedZones": [], "hiddenLayers": []},
    )
    template = legend.json()[0]

    rename = client.patch(
        f"/api/templates/{template['name']}?session_id={uploaded_session}",
        json={"newName": "renamed_symbol"},
    )
    assert rename.status_code == 200
    assert any(item["displayName"] == "renamed_symbol" for item in rename.json())

    delete = client.delete(f"/api/templates/{template['name']}?session_id={uploaded_session}")
    assert delete.status_code == 200
    assert all(item["name"] != template["name"] for item in delete.json())

    clear = client.delete(f"/api/templates?session_id={uploaded_session}")
    assert clear.status_code == 200
    assert clear.json() == []


def test_analyze_sse_returns_reference_result(client: TestClient, uploaded_session: str) -> None:
    response = client.post(
        f"/api/analyze?session_id={uploaded_session}",
        json={"excludedZones": [], "hiddenLayers": []},
    )

    assert response.status_code == 200
    progress_count, result = result_from_sse(response.text)
    assert progress_count == 8
    assert len(result["boxes"]) == 134
    assert sum(item["count"] for item in result["results"]) == 134
    assert result["analysisContext"]["sessionId"] == uploaded_session

    counts = {item["name"]: item["count"] for item in result["results"]}
    assert counts == {
        "05_lokalna_miejscowa_szyna_wyrownawcza": 4,
        "06_gniazdo_230v_pojedyncze_z_uziemieniem": 24,
        "07_gniazdo_230v_podwojne_z_uziemieniem": 30,
        "09_gniazdo_230v_pojedyncze_z_uziemieniem_bryzgoszczelne": 12,
        "10_lacznik_schodowy": 4,
        "11_lacznik_jednobiegunowy": 4,
        "12_lacznik_swiecznikowy": 16,
        "13_wypust_oswietleniowy_sufitowy": 24,
        "14_wypust_oswietleniowy_scienny": 4,
        "19_orurowanie_do_tsm": 12,
    }

    corrected_box = next(box for box in result["boxes"] if box["x"] == 2742 and box["y"] == 975)
    assert corrected_box["symbolName"].startswith("06_")


def test_clear_session(client: TestClient, uploaded_session: str) -> None:
    session_dir = get_session_dir(uploaded_session)
    assert session_dir.exists()

    response = client.post(f"/api/clear?session_id={uploaded_session}")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert not session_dir.exists()
