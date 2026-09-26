"""冒烟测试：只覆盖顺利路径。

这些用例在初始快照上应当全绿；它们不覆盖 README「行为规格」里的边界语义，
因此通过它们并不代表规格已被满足。
"""


def test_root_and_health(client):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["status"] == "running"

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert "models_loaded" in health.json()


def test_encrypt_decrypt_roundtrip(client):
    key = "a" * 32

    enc = client.post("/api/encrypt", data={"content": "# 机密纪要\n讨论内容", "key": key})
    assert enc.status_code == 200
    body = enc.json()
    assert body["success"] is True
    assert body["method"] == "fernet"

    from backend.encrypted_email import MarkdownEncryptor
    encrypted = bytes.fromhex(body["encrypted_data"])
    assert MarkdownEncryptor(key).decrypt_markdown(encrypted) == "# 机密纪要\n讨论内容"


def test_decrypt_endpoint_roundtrip(client):
    from backend.encrypted_email import MarkdownEncryptor

    encryptor = MarkdownEncryptor("b" * 32)
    ciphertext, _ = encryptor.encrypt_markdown("# 会议纪要")

    resp = client.post("/api/decrypt",
                       files={"file": ("minutes.bin", ciphertext, "application/octet-stream")},
                       data={"key": "b" * 32})
    assert resp.status_code == 200
    assert resp.json()["content"] == "# 会议纪要"


def test_gcc_phat_estimates_zero_delay(client):
    import numpy as np
    from backend.source_localization import SoundSourceLocalization

    loc = SoundSourceLocalization()
    rng = np.random.default_rng(0)
    sig = rng.standard_normal(2048)
    assert abs(loc.gcc_phat(sig, sig)) < 1e-9


def test_localization_returns_error_when_output_insufficient(client):
    import numpy as np
    from backend.source_localization import SoundSourceLocalization

    loc = SoundSourceLocalization()
    result = loc.process_localization([np.ones(1024)])
    assert result["success"] is False
    assert "2" in result["error"]


def test_task_lifecycle_endpoints(client):
    import backend.main as main_module

    task_id = "smoke-task"
    main_module.processing_tasks[task_id] = {
        "task_id": task_id, "status": "completed", "progress": 100,
        "message": "done", "created_at": "2026-05-18T10:00:00",
        "result": {"markdown_summary": "# 纪要", "markdown_transcript": "# 转写"},
    }
    assert client.get(f"/api/tasks/{task_id}").status_code == 200
    assert client.get("/api/tasks").status_code == 200
    assert client.get(f"/api/download/{task_id}?file_type=markdown").status_code == 200
    assert client.get(f"/api/download/{task_id}?file_type=json").status_code == 200


def test_summary_markdown_generation(client):
    from backend.summary_generator import OpenAISummaryGenerator

    generator = OpenAISummaryGenerator()
    result = generator.generate_summary({"success": True, "segments": [], "full_text": "会议内容"})
    assert result["success"] is True

    markdown = generator.generate_markdown_summary(result, {"full_text": "会议内容"})
    assert "# 会议纪要" in markdown


def test_transcript_markdown_generation(client):
    from backend.transcriber import MeetingTranscriptIntegrator

    integrator = MeetingTranscriptIntegrator()
    result = integrator.process_meeting_audio("fake.wav")
    assert result["success"] is True

    markdown = integrator.generate_markdown_transcript(result)
    assert "# 会议记录" in markdown
