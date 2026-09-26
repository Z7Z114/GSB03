"""行为规格测试：逐条对应 README「行为规格」的验收点。

这些用例在未修复的实现上应当失败，修复后通过。
"""
import asyncio

import numpy as np
import pytest


# ---------- A. 加密与解密 ----------

def test_encrypt_decrypt_missing_fields_422(client):
    assert client.post("/api/encrypt").status_code == 422
    assert client.post("/api/decrypt").status_code == 422


@pytest.mark.parametrize("bad_key", ["", "   "])
def test_encrypt_rejects_empty_key(client, bad_key):
    resp = client.post("/api/encrypt", data={"content": "# 纪要", "key": bad_key})
    assert resp.status_code == 422


@pytest.mark.parametrize("bad_key", ["", "   "])
def test_decrypt_rejects_empty_key(client, bad_key):
    resp = client.post(
        "/api/decrypt",
        files={"file": ("m.bin", b"ciphertext", "application/octet-stream")},
        data={"key": bad_key},
    )
    assert resp.status_code == 422


def test_encryptor_without_key_marks_method_none():
    from backend.encrypted_email import MarkdownEncryptor

    encryptor = MarkdownEncryptor(encryption_key=None)
    data, method = encryptor.encrypt_markdown("# 内容")
    assert method == "none"
    assert data == "# 内容".encode("utf-8")


def test_decrypt_with_wrong_key_is_explicit_failure(client):
    from backend.encrypted_email import MarkdownEncryptor

    ciphertext, _ = MarkdownEncryptor("k" * 32).encrypt_markdown("# 机密纪要")

    resp = client.post(
        "/api/decrypt",
        files={"file": ("m.bin", ciphertext, "application/octet-stream")},
        data={"key": "x" * 32},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "content" not in body


def test_decrypt_markdown_raises_on_wrong_key_or_no_key():
    from backend.encrypted_email import MarkdownEncryptor

    ciphertext, _ = MarkdownEncryptor("k" * 32).encrypt_markdown("# 机密纪要")

    with pytest.raises(ValueError):
        MarkdownEncryptor("x" * 32).decrypt_markdown(ciphertext)

    with pytest.raises(ValueError):
        MarkdownEncryptor(None).decrypt_markdown(ciphertext)


def test_encrypt_response_reports_method(client):
    resp = client.post("/api/encrypt", data={"content": "# 纪要", "key": "k" * 32})
    assert resp.status_code == 200
    assert resp.json()["method"] == "fernet"


# ---------- B. 邮件发送 ----------

def test_email_not_sent_when_smtp_unconfigured():
    from backend.encrypted_email import EmailSender

    sender = EmailSender()
    result = sender.send_encrypted_email(["a@b.com"], "主题", "# 内容")
    assert result["success"] is False
    assert result.get("error") or result.get("message")


def test_dispatch_email_success_reflects_reality(tmp_path):
    from backend.encrypted_email import MeetingMinutesDispatcher

    dispatcher = MeetingMinutesDispatcher(encryption_key="k" * 32)
    result = dispatcher.generate_and_dispatch(
        markdown_content="# 纪要",
        to_emails=["a@b.com"],
        output_dir=str(tmp_path),
        send_email=True,
    )
    assert result["email"] is not None
    assert result["email"]["success"] is False


# ---------- C. 任务与下载 ----------

def test_empty_audio_upload_rejected(client):
    before = len(client.get("/api/tasks").json())
    resp = client.post(
        "/api/process/audio",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert resp.status_code == 400
    after = len(client.get("/api/tasks").json())
    assert after == before


def test_update_task_status_rejects_unknown_status():
    import backend.main as main_module

    with pytest.raises(ValueError):
        main_module.update_task_status("task-x", "bogus-status", 0, "msg")


def test_download_guards(client):
    import backend.main as main_module

    assert client.get("/api/download/unknown-task").status_code == 404

    main_module.processing_tasks["spec-running"] = {
        "task_id": "spec-running", "status": "processing", "progress": 50,
        "message": "running", "created_at": "2026-05-18T10:00:00", "result": None,
    }
    assert client.get("/api/download/spec-running").status_code == 400

    main_module.processing_tasks["spec-done"] = {
        "task_id": "spec-done", "status": "completed", "progress": 100,
        "message": "done", "created_at": "2026-05-18T10:00:00",
        "result": {"markdown_transcript": "# 转写"},
    }
    assert client.get("/api/download/spec-done?file_type=pdf").status_code == 400


# ---------- D. 声源定位 ----------

def _two_mic_files():
    return [
        ("files", ("mic1.wav", b"fake-audio-1", "audio/wav")),
        ("files", ("mic2.wav", b"fake-audio-2", "audio/wav")),
    ]


def test_localization_rejects_invalid_params(client):
    assert client.post("/api/process/localization?scan_range=-1",
                       files=_two_mic_files()).status_code == 422
    assert client.post("/api/process/localization?scan_range=0",
                       files=_two_mic_files()).status_code == 422
    assert client.post("/api/process/localization?resolution=1",
                       files=_two_mic_files()).status_code == 422
    assert client.post("/api/process/localization?resolution=0",
                       files=_two_mic_files()).status_code == 422


def test_localization_requires_two_signals(client):
    resp = client.post(
        "/api/process/localization",
        files=[("files", ("mic1.wav", b"fake-audio-1", "audio/wav"))],
    )
    assert resp.status_code == 400


def test_localization_missing_audio_deps_is_503(client):
    import backend.main as main_module

    if main_module.LIBROSA_AVAILABLE:
        pytest.skip("librosa 已安装，走真实分支")
    resp = client.post("/api/process/localization", files=_two_mic_files())
    assert resp.status_code == 503


def test_gcc_phat_empty_signal_is_predictable():
    from backend.source_localization import SoundSourceLocalization

    loc = SoundSourceLocalization()
    assert loc.gcc_phat(np.array([]), np.array([])) == 0.0
    assert loc.gcc_phat(np.ones(128), np.array([])) == 0.0


def test_scan_for_sources_tiny_resolution_no_crash():
    from backend.source_localization import SoundSourceLocalization

    loc = SoundSourceLocalization()
    rng = np.random.default_rng(1)
    signals = [rng.standard_normal(512) for _ in range(2)]
    for bad_resolution in (0, 1):
        result = loc.scan_for_sources(signals, resolution=bad_resolution)
        assert result["sources"] == []
        assert result["power_map"] == []


def test_real_time_update_single_channel_returns_position_and_confidence():
    from backend.source_localization import SoundSourceLocalization

    loc = SoundSourceLocalization()
    rng = np.random.default_rng(2)

    update = loc.real_time_localization_update(rng.standard_normal(256))
    assert "position" in update
    assert "confidence" in update
    assert len(update["position"]) == 3

    update = loc.real_time_localization_update(np.ones(128), previous_estimate=[1.0, 2.0, 3.0])
    assert update["position"] == [1.0, 2.0, 3.0]
    assert update["confidence"] == 0.0


# ---------- E. 转写与说话人 ----------

def test_diarize_rejects_nonpositive_num_speakers():
    from backend.transcriber import PyannoteDiarizer

    diarizer = PyannoteDiarizer()
    for bad in (0, -1):
        result = diarizer.diarize("fake.wav", num_speakers=bad)
        assert result["success"] is False
        assert result.get("error")


def test_offline_transcription_is_identifiable():
    from backend.transcriber import WhisperTranscriber

    transcriber = WhisperTranscriber()
    if transcriber.model is not None:
        pytest.skip("Whisper 模型已加载，走真实分支")
    result = transcriber.transcribe("fake.wav")
    assert result["success"] is True
    assert result.get("note")


def test_process_meeting_audio_keeps_contract_fields():
    from backend.transcriber import MeetingTranscriptIntegrator

    integrator = MeetingTranscriptIntegrator()
    result = integrator.process_meeting_audio("fake.wav", num_speakers=-1)
    assert result["success"] is True
    for field in ("success", "full_text", "segments", "speaker_stats"):
        assert field in result


# ---------- F. WebSocket 广播 ----------

class _FakeWebSocket:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.received = []

    async def send_json(self, message):
        if self.fail:
            raise RuntimeError("connection broken")
        self.received.append(message)


def test_broadcast_removes_broken_connection_and_continues():
    from backend.main import ConnectionManager

    manager = ConnectionManager()
    good1, good2, bad = _FakeWebSocket(), _FakeWebSocket(), _FakeWebSocket(fail=True)
    manager.active_connections.extend([bad, good1, good2])

    asyncio.run(manager.broadcast({"type": "test"}))

    assert good1.received == [{"type": "test"}]
    assert good2.received == [{"type": "test"}]
    assert bad not in manager.active_connections
    assert len(manager.active_connections) == 2


def test_disconnect_is_idempotent():
    from backend.main import ConnectionManager

    manager = ConnectionManager()
    ws = _FakeWebSocket()
    manager.disconnect(ws)
    manager.active_connections.append(ws)
    manager.disconnect(ws)
    manager.disconnect(ws)
    assert manager.active_connections == []
