import io

from fastapi.testclient import TestClient
from PIL import Image

import api.main as api_main


def _tiny_png_bytes() -> bytes:
    # Keep a deterministic valid PNG payload for upload validation tests.
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
    return buf.getvalue()


def test_path2_disabled_returns_503(monkeypatch):
    monkeypatch.setenv("ENABLE_PATH2_IMAGE_SEARCH", "false")
    client = TestClient(api_main.app)

    resp = client.post(
        "/api/path2/image-search",
        files={"image": ("query.png", _tiny_png_bytes(), "image/png")},
        data={"session_id": "s1", "top_k": "3"},
    )
    assert resp.status_code == 503
    assert "disabled" in resp.text.lower()


def test_path2_rejects_non_png(monkeypatch):
    monkeypatch.setenv("ENABLE_PATH2_IMAGE_SEARCH", "true")
    client = TestClient(api_main.app)

    resp = client.post(
        "/api/path2/image-search",
        files={"image": ("query.jpg", b"not-png", "image/jpeg")},
        data={"session_id": "s1", "top_k": "3"},
    )
    assert resp.status_code == 415
    assert ".png" in resp.text.lower()


def test_path2_success_returns_products(monkeypatch):
    monkeypatch.setenv("ENABLE_PATH2_IMAGE_SEARCH", "true")
    monkeypatch.setattr(
        api_main,
        "_run_path2_image_search",
        lambda raw, top_k: [
            {
                "image_id": "img-1",
                "image_path": "img-1.png",
                "label": "Blazer",
                "color": "White",
                "caption": "sample",
                "score": 0.99,
            }
        ][:top_k],
    )
    client = TestClient(api_main.app)

    resp = client.post(
        "/api/path2/image-search",
        files={"image": ("query.png", _tiny_png_bytes(), "image/png")},
        data={"session_id": "s1", "top_k": "1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "path2"
    assert body["count"] == 1
    assert body["products"][0]["image_id"] == "img-1"


def test_path1_contract_unchanged_with_path2_toggle(monkeypatch):
    client = TestClient(api_main.app)

    monkeypatch.setenv("ENABLE_PATH2_IMAGE_SEARCH", "false")
    resp_disabled = client.post("/api/chat/stream", json={})
    assert resp_disabled.status_code == 422

    monkeypatch.setenv("ENABLE_PATH2_IMAGE_SEARCH", "true")
    resp_enabled = client.post("/api/chat/stream", json={})
    assert resp_enabled.status_code == 422
