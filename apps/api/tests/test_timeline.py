from explainer.domain import Brief
from explainer.services.ingestion import analyze
from explainer.services.planning import template_plan
from explainer.adapters.voice import estimated_cues
from explainer.services.quality import inspect


def test_caption_bounds():
    text = "这是第一句。第二句包含 API。最后一句用于测试。"
    cues = estimated_cues(text, 8.3)
    assert cues[0]["start"] == 0
    assert abs(cues[-1]["end"] - 8.3) < 0.001
    assert all(c["end"] > c["start"] for c in cues)
    assert "".join(c["text"] for c in cues) == text


def test_quality_rejects_fabricated_runtime():
    brief = Brief(title="Test", prompt="Explain APIs")
    content = analyze(brief)
    board = template_plan(content, brief)
    cursor = 0
    for s in board.scenes:
        s.start_frame, s.frames = cursor, 300
        cursor += 300
    board.total_frames = cursor
    board.scenes[0].verification = "runtime"
    board.scenes[0].claim_ids = ["nonexistent"]
    report = inspect(board, content, {"state": "unavailable", "message": "No sandbox"}, [], 50)
    codes = {f["code"] for f in report["findings"] if f["severity"] == "error"}
    assert {"FALSE_RUNTIME", "UNKNOWN_EVIDENCE"} <= codes
