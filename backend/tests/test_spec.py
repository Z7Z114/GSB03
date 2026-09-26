"""行为规格测试：逐条对应 README「行为规格」的验收点。

这些用例在未修复的初始快照上应当失败，修复后通过。
"""
import asyncio

import numpy as np
import pytest


# ---------- A. 加密与解密 ----------

def test_encrypt_response_marks_encryption_method(client):
    resp = client.post("/api/encrypt", data={"content": "# 纪要", "key": "k" * 32})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["method"] == "fernet"
    assert body["encrypted"] is True


def test_decrypt_with_wrong_key_reports_failure(client):
    from backend.encrypted_email import MarkdownEncryptor

    ciphertext, _ = MarkdownEncryptor("a" * 32).encrypt_markdown("# 机密")
    resp = client.post(
        "/api/decrypt",
        files={"file": ("x.bin", ciphertext, "application/octet-stream")},
        data={"key": "b" * 32},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


def test_decryptor_raises_on_wrong_key(client):
    from backend.encrypted_email import MarkdownEncryptor

    ciphertext, _ = MarkdownEncryptor("a" * 32).encrypt_markdown("# 机密")
    with pytest.raises(ValueError):
        MarkdownEncryptor("b" * 32).decrypt_markdown(ciphertext)


def test_decryptor_without_key_raises(client):
    from backend.encrypted_email import MarkdownEncryptor

    with pytest.raises(ValueError):
        MarkdownEncryptor(None).decrypt_markdown(b"whatever")


# ---------- B. 邮件发送 ----------

def test_email_not_configured_reports_not_sent(client):
    from backend.encrypted_email import EmailSender

    result = EmailSender().send_encrypted_email(["a@b.c"], "主题", "# 内容")
    assert result["success"] is False
    assert result.get("error")


def test_dispatcher_email_success_matches_delivery(client, tmp_path):
    from backend.encrypted_email import MeetingMinutesDispatcher

    result = MeetingMinutesDispatcher().generate_and_dispatch(
        markdown_content="# 纪要",
        to_emails=["a@b.c"],
        output_dir=str(tmp_path),
        send_email=True,
    )
    assert result["email"] is not None
    assert result["email"]["success"] is False


# ---------- C. 任务与下载 ----------

def test_empty_audio_upload_rejected(client):
    import backend.main as main_module

    before = len(main_module.processing_tasks)
    resp = client.post(
        "/api/process/audio",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert resp.status_code == 400
    assert len(main_module.processing_tasks) == before


# ---------- D. 声源定位 ----------

def _two_mic_files():
    return [
        ("files", ("m1.wav", b"fake", "audio/wav")),
        ("files", ("m2.wav", b"fake", "audio/wav")),
    ]


def test_localization_invalid_scan_range_422(client):
    resp = client.post("/api/process/localization?scan_range=-1", files=_two_mic_files())
    assert resp.status_code == 422


def test_localization_invalid_resolution_422(client):
    for bad in (0, 1):
        resp = client.post(
            f"/api/process/localization?resolution={bad}", files=_two_mic_files()
        )
        assert resp.status_code == 422


def test_gcc_phat_empty_signal(client):
    from backend.source_localization import SoundSourceLocalization

    loc = SoundSourceLocalization()
    assert loc.gcc_phat(np.array([]), np.ones(16)) == 0.0
    assert loc.gcc_phat(np.ones(16), np.array([])) == 0.0


def test_scan_for_sources_rejects_tiny_resolution(client):
    from backend.source_localization import SoundSourceLocalization

    loc = SoundSourceLocalization()
    rng = np.random.default_rng(0)
    signals = [rng.standard_normal(256) for _ in range(2)]
    for bad in (0, 1):
        result = loc.scan_for_sources(signals, resolution=bad)
        assert result["sources"] == []


def test_real_time_update_single_channel(client):
    from backend.source_localization import SoundSourceLocalization

    loc = SoundSourceLocalization()
    update = loc.real_time_localization_update(np.ones(512))
    assert "position" in update
    assert "confidence" in update
    assert len(update["position"]) == 3


def test_real_time_update_single_channel_with_previous(client):
    from backend.source_localization import SoundSourceLocalization

    loc = SoundSourceLocalization()
    prev = np.array([1.0, 2.0, 3.0])
    update = loc.real_time_localization_update(np.ones(512), previous_estimate=prev)
    assert update["position"] == [1.0, 2.0, 3.0]
    assert update["confidence"] == 0.0


# ---------- E. 转写与说话人 ----------

def test_diarize_rejects_nonpositive_num_speakers(client):
    from backend.transcriber import PyannoteDiarizer

    diarizer = PyannoteDiarizer()
    for bad in (0, -1):
        with pytest.raises(ValueError):
            diarizer.diarize("fake.wav", num_speakers=bad)


def test_process_meeting_audio_rejects_nonpositive_num_speakers(client):
    from backend.transcriber import MeetingTranscriptIntegrator

    integrator = MeetingTranscriptIntegrator()
    result = integrator.process_meeting_audio("fake.wav", num_speakers=0)
    assert result["success"] is False
    assert "num_speakers" in result["error"]


# ---------- F. WebSocket 广播 ----------

def test_broadcast_drops_dead_connections(client):
    import backend.main as main_module

    class FakeWebSocket:
        def __init__(self, fail=False):
            self.fail = fail
            self.received = []

        async def send_json(self, message):
            if self.fail:
                raise RuntimeError("connection broken")
            self.received.append(message)

    manager = main_module.ConnectionManager()
    dead = FakeWebSocket(fail=True)
    alive = FakeWebSocket()
    manager.active_connections.extend([dead, alive])

    asyncio.run(manager.broadcast({"type": "test"}))

    assert alive.received == [{"type": "test"}]
    assert dead not in manager.active_connections
    assert alive in manager.active_connections
