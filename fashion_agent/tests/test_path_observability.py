import io

from fastapi.testclient import TestClient
from PIL import Image

import api.main as api_main
import agent.fashion_agent as fashion_agent
import agent.memory as memory
from agent.intent_classifier import ClassifiedIntent, ExtractedSlots


def _tiny_png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
    return buf.getvalue()


def test_click_endpoint_forwards_path_mode(monkeypatch):
    captured = {}

    def fake_log_click(session_id, image_id, position, search_query="", path_mode="path1"):
        captured.update(
            {
                "session_id": session_id,
                "image_id": image_id,
                "position": position,
                "search_query": search_query,
                "path_mode": path_mode,
            }
        )

    monkeypatch.setattr(memory, "log_click", fake_log_click)
    client = TestClient(api_main.app)

    resp = client.post(
        "/api/sessions/s1/clicks",
        json={
            "image_id": "img-1",
            "position": 2,
            "search_query": "white shirt",
            "path_mode": "path2",
        },
    )
    assert resp.status_code == 200
    assert captured["path_mode"] == "path2"


def test_intent_endpoint_forwards_path_mode(monkeypatch):
    captured = {}

    def fake_log_intent(session_id, image_id, intent_type, reason="", path_mode="path1"):
        captured.update(
            {
                "session_id": session_id,
                "image_id": image_id,
                "intent_type": intent_type,
                "reason": reason,
                "path_mode": path_mode,
            }
        )

    monkeypatch.setattr(memory, "log_intent", fake_log_intent)
    client = TestClient(api_main.app)

    resp = client.post(
        "/api/sessions/s1/intents",
        json={
            "image_id": "img-2",
            "intent_type": "will_buy",
            "reason": "nice fit",
            "path_mode": "path2",
        },
    )
    assert resp.status_code == 200
    assert captured["path_mode"] == "path2"


def test_path2_image_search_logs_impressions_and_caches_context(monkeypatch):
    monkeypatch.setenv("ENABLE_PATH2_IMAGE_SEARCH", "true")

    products = [
        {
            "image_id": "img-1",
            "image_path": "img-1.png",
            "label": "Blazer",
            "color": "White",
            "caption": "sample",
            "score": 0.99,
        }
    ]
    monkeypatch.setattr(api_main, "_run_path2_image_search", lambda raw, top_k: products[:top_k])

    impression_calls = {}
    cache_calls = {}

    def fake_log_impression_batch(session_id, items):
        impression_calls["session_id"] = session_id
        impression_calls["items"] = items
        return len(items)

    def fake_cache_external_results(session_id, path_mode, cached_products):
        cache_calls["session_id"] = session_id
        cache_calls["path_mode"] = path_mode
        cache_calls["products"] = cached_products

    monkeypatch.setattr(memory, "log_impression_batch", fake_log_impression_batch)
    monkeypatch.setattr(api_main, "cache_external_results", fake_cache_external_results)

    client = TestClient(api_main.app)
    resp = client.post(
        "/api/path2/image-search",
        files={"image": ("query.png", _tiny_png_bytes(), "image/png")},
        data={"session_id": "s1", "top_k": "1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["products"][0]["path_mode"] == "path2"
    assert impression_calls["session_id"] == "s1"
    assert impression_calls["items"][0]["path_mode"] == "path2"
    assert cache_calls["path_mode"] == "path2"


def test_selection_context_isolation_uses_latest_path_cache(monkeypatch):
    session_id = "s-isolated"
    monkeypatch.setattr(fashion_agent, "add_message", lambda *args, **kwargs: None)

    fashion_agent.cache_external_results(
        session_id,
        "path1",
        [{"image_id": "p1-a", "image_path": "p1-a.png", "label": "Shirt", "score": 0.1}],
    )
    fashion_agent.cache_external_results(
        session_id,
        "path2",
        [{"image_id": "p2-a", "image_path": "p2-a.png", "label": "Dress", "score": 0.2}],
    )

    list(fashion_agent._handle_product_select(session_id, [1], "q", "pick 1"))
    pending = fashion_agent._session_pending_selection.get(session_id)
    assert pending is not None
    assert pending.path_mode == "path2"
    assert pending.items[0].image_id == "p2-a"


def test_integrity_detects_clicks_without_impressions():
    integrity = memory._evaluate_funnel_integrity(
        impressions=0,
        clicks=1,
        cart_adds=0,
        will_buy=0,
        not_for_me=0,
        converted=False,
    )
    assert not integrity["valid"]
    assert "clicks_without_impressions" in integrity["issues"]


def test_integrity_valid_for_complete_funnel():
    integrity = memory._evaluate_funnel_integrity(
        impressions=5,
        clicks=3,
        cart_adds=2,
        will_buy=1,
        not_for_me=1,
        converted=True,
    )
    assert integrity["valid"]
    assert integrity["issues"] == []


def test_behaviour_funnel_includes_path_comparison_and_integrity(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET_KEY", "secret")

    class _FakeCursor:
        def execute(self, *_args, **_kwargs):
            return None

        def fetchall(self):
            return [{"session_id": "s1", "user_name": "u1", "gender": "male", "age": 24}]

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    class _FakeConn:
        def cursor(self, **_kwargs):
            return _FakeCursor()

        def close(self):
            return None

    monkeypatch.setattr("psycopg2.connect", lambda **_kwargs: _FakeConn())
    monkeypatch.setattr(
        memory,
        "get_session_funnel",
        lambda _sid: {
            "session_id": "s1",
            "model_name": "gemini",
            "total_tokens": 100,
            "impressions": 5,
            "clicks": 3,
            "cart_adds": 2,
            "will_buy": 1,
            "not_for_me": 0,
            "converted": True,
            "ctr": 0.6,
            "cart_rate": 0.667,
            "intent_rate": 0.5,
            "precision_at_k": 0.2,
            "integrity": {"valid": True, "issues": []},
        },
    )
    monkeypatch.setattr(
        memory,
        "get_session_funnel_by_path",
        lambda _sid: [
            {
                "path_mode": "path1",
                "impressions": 3,
                "clicks": 2,
                "cart_adds": 1,
                "will_buy": 1,
                "not_for_me": 0,
                "converted": True,
                "ctr": 0.667,
                "cart_rate": 0.5,
                "intent_rate": 1.0,
                "precision_at_k": 0.333,
                "integrity": {"valid": True, "issues": []},
            },
            {
                "path_mode": "path2",
                "impressions": 2,
                "clicks": 1,
                "cart_adds": 1,
                "will_buy": 0,
                "not_for_me": 0,
                "converted": False,
                "ctr": 0.5,
                "cart_rate": 1.0,
                "intent_rate": 0.0,
                "precision_at_k": 0.0,
                "integrity": {"valid": True, "issues": []},
            },
        ],
    )

    client = TestClient(api_main.app)
    resp = client.get("/api/analytics/behaviour-funnel", headers={"X-Admin-Key": "secret"})
    assert resp.status_code == 200
    body = resp.json()
    assert "path_comparison" in body
    assert "integrity" in body


def test_path_mode_accepts_path1_only_path2_only_and_mixed_inputs(monkeypatch):
    captured_batches = []

    def fake_log_impression_batch(_session_id, items):
        captured_batches.append(items)
        return len(items)

    monkeypatch.setattr(memory, "log_impression_batch", fake_log_impression_batch)
    client = TestClient(api_main.app)

    # PATH 1 only
    resp1 = client.post(
        "/api/sessions/s1/impressions",
        json={"items": [{"image_id": "a", "position": 1, "path_mode": "path1"}]},
    )
    assert resp1.status_code == 200

    # PATH 2 only
    resp2 = client.post(
        "/api/sessions/s1/impressions",
        json={"items": [{"image_id": "b", "position": 1, "path_mode": "path2"}]},
    )
    assert resp2.status_code == 200

    # Mixed
    resp3 = client.post(
        "/api/sessions/s1/impressions",
        json={
            "items": [
                {"image_id": "c", "position": 1, "path_mode": "path1"},
                {"image_id": "d", "position": 2, "path_mode": "path2"},
            ]
        },
    )
    assert resp3.status_code == 200
    assert captured_batches[-1][0]["path_mode"] == "path1"
    assert captured_batches[-1][1]["path_mode"] == "path2"


def test_search_query_resolution_blocks_low_confidence_before_search():
    session_id = "sid-low-conf"
    fashion_agent._session_accumulated_slots.pop(session_id, None)

    intent_result = ClassifiedIntent(
        intent="text_search",
        confidence=0.5,
        filters={},
        refined_query="white cotton shirt",
        extracted_slots=ExtractedSlots(
            category="Shirt",
            color="white",
            fabric="cotton",
        ),
    )

    search_query, clarification, _slots = fashion_agent._resolve_search_query(
        "text_search",
        intent_result,
        session_id,
        history=[],
        query="show me a white shirt",
    )

    assert search_query == ""
    assert clarification.strip() != ""


def test_search_query_resolution_blocks_when_required_slots_missing():
    session_id = "sid-missing-slots"
    fashion_agent._session_accumulated_slots.pop(session_id, None)

    intent_result = ClassifiedIntent(
        intent="text_search",
        confidence=0.95,
        filters={},
        refined_query="shirt",
        extracted_slots=ExtractedSlots(category="Shirt"),
    )

    search_query, clarification, _slots = fashion_agent._resolve_search_query(
        "text_search",
        intent_result,
        session_id,
        history=[],
        query="show shirt",
    )

    assert search_query == ""
    assert clarification.strip() != ""


def test_search_query_resolution_merges_slots_after_clarification():
    session_id = "sid-slot-merge"
    fashion_agent._session_accumulated_slots.pop(session_id, None)

    first_turn = ClassifiedIntent(
        intent="text_search",
        confidence=0.95,
        filters={},
        refined_query="shirt",
        extracted_slots=ExtractedSlots(category="Shirt"),
    )
    sq1, clarification1, _slots1 = fashion_agent._resolve_search_query(
        "text_search",
        first_turn,
        session_id,
        history=[],
        query="show shirts",
    )
    assert sq1 == ""
    assert clarification1.strip() != ""

    second_turn = ClassifiedIntent(
        intent="follow_up",
        confidence=0.95,
        filters={},
        refined_query="blue regular fit",
        extracted_slots=ExtractedSlots(color="blue", fit="regular fit"),
    )
    sq2, clarification2, _slots2 = fashion_agent._resolve_search_query(
        "follow_up",
        second_turn,
        session_id,
        history=[],
        query="blue regular fit",
    )
    assert clarification2 == ""
    assert "Shirt" in sq2
    assert "blue" in sq2


def test_outfit_request_requires_more_than_single_signal():
    session_id = "sid-outfit-single-signal"
    fashion_agent._session_accumulated_slots.pop(session_id, None)
    fashion_agent._session_ranked_slots.pop(session_id, None)

    intent_result = ClassifiedIntent(
        intent="outfit_request",
        confidence=0.92,
        filters={"occasion": "date"},
        refined_query="date outfit",
        extracted_slots=ExtractedSlots(),
    )

    search_query, clarification, _slots = fashion_agent._resolve_search_query(
        "outfit_request",
        intent_result,
        session_id,
        history=[],
        query="tôi muốn tìm một bộ quần áo để đi hẹn hò",
    )

    assert search_query == ""
    assert clarification.strip() != ""


def test_outfit_request_queries_when_occasion_and_style_present():
    session_id = "sid-outfit-ready"
    fashion_agent._session_accumulated_slots.pop(session_id, None)
    fashion_agent._session_ranked_slots.pop(session_id, None)

    intent_result = ClassifiedIntent(
        intent="outfit_request",
        confidence=0.92,
        filters={"occasion": "date", "style": "elegant"},
        refined_query="date elegant outfit",
        extracted_slots=ExtractedSlots(),
    )

    search_query, clarification, _slots = fashion_agent._resolve_search_query(
        "outfit_request",
        intent_result,
        session_id,
        history=[],
        query="outfit for a date, elegant style",
    )

    assert clarification == ""
    assert "date" in search_query.lower()
    assert "elegant" in search_query.lower()


def test_direct_selection_endpoint_persists_path2_item(monkeypatch):
    captured = {}

    def fake_save_selected_items(session_id, items):
        captured["session_id"] = session_id
        captured["items"] = items
        return 1

    monkeypatch.setattr(memory, "save_selected_items", fake_save_selected_items)
    client = TestClient(api_main.app)

    resp = client.post(
        "/api/sessions/s1/selections",
        json={
            "image_id": "img-p2-1",
            "label": "Dress",
            "color": "Blue",
            "caption": "sample caption",
            "image_path": "img-p2-1.jpg",
            "search_query": "__path2_image__",
            "position": 2,
            "path_mode": "path2",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["inserted"] == 1
    assert body["already_exists"] == 0
    assert captured["session_id"] == "s1"
    assert captured["items"][0]["path_mode"] == "path2"


def test_direct_selection_endpoint_rejects_invalid_payload():
    client = TestClient(api_main.app)

    resp = client.post(
        "/api/sessions/s1/selections",
        json={
            "image_id": "",
            "label": "Dress",
            "image_path": "img.jpg",
            "position": 1,
            "path_mode": "path2",
        },
    )
    assert resp.status_code == 400
    assert "image_id" in resp.text


def test_direct_selection_endpoint_reports_duplicate_insertion(monkeypatch):
    monkeypatch.setattr(memory, "save_selected_items", lambda _sid, _items: 0)
    client = TestClient(api_main.app)

    resp = client.post(
        "/api/sessions/s1/selections",
        json={
            "image_id": "img-p2-1",
            "label": "Dress",
            "image_path": "img-p2-1.jpg",
            "position": 1,
            "path_mode": "path2",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["inserted"] == 0
    assert body["already_exists"] == 1
