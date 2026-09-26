import os
import asyncio
import tempfile
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import numpy as np
from dotenv import load_dotenv

try:  # 音频依赖可选：缺失时模块仍可导入，相关能力在调用时给出明确错误
    import soundfile as sf
    AUDIO_IO_AVAILABLE = True
except ImportError:
    sf = None
    AUDIO_IO_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    librosa = None
    LIBROSA_AVAILABLE = False

from .audio_processor import LaserAudioProcessor
from .source_localization import SoundSourceLocalization
from .transcriber import MeetingTranscriptIntegrator
from .summary_generator import OpenAISummaryGenerator
from .encrypted_email import MeetingMinutesDispatcher

load_dotenv()

app = FastAPI(
    title="Laser Vibrometry Spy System API",
    description="Remote audio acquisition and meeting minutes generation system for authorized security testing",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audio_processor = LaserAudioProcessor()
localization = SoundSourceLocalization()

transcript_integrator = MeetingTranscriptIntegrator(
    whisper_model=os.getenv("WHISPER_MODEL", "large-v3")
)

summary_generator = OpenAISummaryGenerator(
    model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
)

dispatcher = MeetingMinutesDispatcher()

processing_tasks = {}
active_connections: List[WebSocket] = []


class AudioProcessingRequest(BaseModel):
    num_speakers: Optional[int] = Field(None, description="Expected number of speakers")
    language: str = Field("zh", description="Language code (zh, en, etc.)")
    generate_summary: bool = Field(True, description="Generate AI summary")
    send_email: bool = Field(False, description="Send encrypted email")
    recipient_emails: Optional[List[str]] = Field(None, description="Email recipients")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for summary")


class ProcessingStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str
    created_at: str
    result: Optional[Dict] = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict):
        stale_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                stale_connections.append(connection)
        for connection in stale_connections:
            self.disconnect(connection)


manager = ConnectionManager()

TASK_STATUSES = {"queued", "processing", "completed", "failed"}


@app.get("/")
async def root():
    return {
        "name": "Laser Vibrometry Spy System API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "audio_processing": "/api/process/audio",
            "localization": "/api/process/localization",
            "tasks": "/api/tasks/{task_id}",
            "websocket": "/ws/realtime"
        }
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": {
            "whisper": transcript_integrator.transcriber.model is not None,
            "pyannote": transcript_integrator.diarizer.pipeline is not None,
            "openai": summary_generator.client is not None
        }
    }


@app.post("/api/process/audio")
async def process_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: AudioProcessingRequest = None
):
    task_id = str(uuid.uuid4())
    request = request or AudioProcessingRequest()

    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read uploaded file: {e}")

    if not contents:
        raise HTTPException(status_code=400, detail="上传的音频文件为空，无法创建处理任务")

    processing_tasks[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress": 0,
        "message": "Task queued for processing",
        "created_at": datetime.now().isoformat(),
        "result": None
    }

    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, f"input_{task_id}.wav")

    try:
        with open(input_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        processing_tasks.pop(task_id, None)
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    background_tasks.add_task(
        process_audio_background,
        task_id,
        input_path,
        request
    )

    return processing_tasks[task_id]


async def process_audio_background(
    task_id: str,
    input_path: str,
    request: AudioProcessingRequest
):
    try:
        update_task_status(task_id, "processing", 10, "Loading and preprocessing audio...")
        await manager.broadcast({
            "type": "task_update",
            "task_id": task_id,
            "status": "processing",
            "progress": 10,
            "message": "Loading and preprocessing audio..."
        })

        enhanced_audio, enhanced_path = audio_processor.process_audio_file(
            input_path,
            output_path=input_path.replace("input_", "enhanced_")
        )

        update_task_status(task_id, "processing", 30, "Audio enhancement complete. Starting transcription...")
        await manager.broadcast({
            "type": "task_update",
            "task_id": task_id,
            "status": "processing",
            "progress": 30,
            "message": "Audio enhancement complete. Starting transcription..."
        })

        transcript_result = transcript_integrator.process_meeting_audio(
            enhanced_path,
            num_speakers=request.num_speakers,
            language=request.language
        )

        if not transcript_result["success"]:
            update_task_status(task_id, "failed", 100, f"Transcription failed: {transcript_result.get('error')}")
            return

        update_task_status(task_id, "processing", 60, "Transcription complete. Generating summary...")
        await manager.broadcast({
            "type": "task_update",
            "task_id": task_id,
            "status": "processing",
            "progress": 60,
            "message": "Transcription complete. Generating summary..."
        })

        result = {
            "transcript": transcript_result,
            "summary": None,
            "markdown_transcript": transcript_integrator.generate_markdown_transcript(transcript_result),
            "email_result": None
        }

        if request.generate_summary:
            summary_result = summary_generator.generate_summary(
                transcript_result,
                context=request.context
            )
            result["summary"] = summary_result
            result["markdown_summary"] = summary_generator.generate_markdown_summary(
                summary_result,
                transcript_result
            )

            update_task_status(task_id, "processing", 85, "Summary generated.")
            await manager.broadcast({
                "type": "task_update",
                "task_id": task_id,
                "status": "processing",
                "progress": 85,
                "message": "Summary generated."
            })

        if request.send_email and request.recipient_emails:
            markdown_content = result.get("markdown_summary", result["markdown_transcript"])
            email_result = dispatcher.generate_and_dispatch(
                markdown_content=markdown_content,
                to_emails=request.recipient_emails,
                send_email=True
            )
            result["email_result"] = email_result

        update_task_status(task_id, "completed", 100, "Processing complete", result)
        await manager.broadcast({
            "type": "task_complete",
            "task_id": task_id,
            "result": result
        })

    except Exception as e:
        update_task_status(task_id, "failed", 100, f"Processing failed: {str(e)}")
        await manager.broadcast({
            "type": "task_error",
            "task_id": task_id,
            "error": str(e)
        })


def update_task_status(task_id: str, status: str, progress: float, message: str, result: Optional[Dict] = None):
    if status not in TASK_STATUSES:
        raise ValueError(f"未知任务状态: {status}（允许值: {sorted(TASK_STATUSES)}）")
    if task_id in processing_tasks:
        processing_tasks[task_id].update({
            "status": status,
            "progress": progress,
            "message": message,
            "result": result
        })


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return processing_tasks[task_id]


@app.get("/api/tasks")
async def list_tasks():
    return list(processing_tasks.values())


def _require_librosa():
    if not LIBROSA_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="音频依赖 librosa 未安装：请安装 requirements-ml.txt"
        )


@app.post("/api/process/localization")
async def process_localization(
    files: List[UploadFile] = File(...),
    scan_range: float = 5.0,
    resolution: int = 50
):
    if scan_range <= 0:
        raise HTTPException(status_code=422, detail="scan_range 必须为正数")
    if resolution < 2:
        raise HTTPException(status_code=422, detail="resolution 必须为 >= 2 的正整数")

    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least 2 microphone signals required for localization")

    _require_librosa()

    audio_signals = []
    temp_files = []

    try:
        for file in files:
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, file.filename)
            contents = await file.read()
            with open(temp_path, "wb") as f:
                f.write(contents)
            temp_files.append(temp_path)

            y, sr = librosa.load(temp_path, sr=audio_processor.sample_rate, mono=True)
            audio_signals.append(y)

        localization_result = localization.process_localization(
            audio_signals,
            scan_range=(-scan_range, scan_range),
            resolution=resolution
        )

        return {
            "success": True,
            "localization": localization_result,
            "num_microphones": len(files),
            "scan_range": scan_range,
            "resolution": resolution
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Localization failed: {e}")
    finally:
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass


@app.get("/api/download/{task_id}")
async def download_result(task_id: str, file_type: str = "markdown"):
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = processing_tasks[task_id]
    if task["status"] != "completed" or not task["result"]:
        raise HTTPException(status_code=400, detail="Task not completed or no result available")

    result = task["result"]

    if file_type == "markdown":
        content = result.get("markdown_summary", result.get("markdown_transcript", ""))
        filename = f"meeting_minutes_{task_id}.md"
        media_type = "text/markdown"
    elif file_type == "json":
        import json
        content = json.dumps(result, ensure_ascii=False, indent=2)
        filename = f"meeting_data_{task_id}.json"
        media_type = "application/json"
    else:
        raise HTTPException(status_code=400, detail="Invalid file type. Use 'markdown' or 'json'")

    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f"_{filename}")
    temp_file.write(content)
    temp_file.close()

    return FileResponse(
        temp_file.name,
        media_type=media_type,
        filename=filename
    )


@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})

            elif data.get("type") == "audio_chunk":
                try:
                    chunk_data = np.array(data.get("audio_data", []), dtype=np.float32)

                    loc_update = localization.real_time_localization_update(chunk_data)

                    await manager.broadcast({
                        "type": "localization_update",
                        "position": loc_update["position"],
                        "confidence": loc_update.get("confidence", 0),
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Error processing audio chunk: {str(e)}"
                    })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)


@app.post("/api/decrypt")
async def decrypt_file(file: UploadFile = File(...), key: str = Form(...)):
    if not key or not key.strip():
        raise HTTPException(status_code=422, detail="key 不能为空")
    try:
        from .encrypted_email import MarkdownEncryptor
        
        encryptor = MarkdownEncryptor(encryption_key=key)
        
        contents = await file.read()
        decrypted = encryptor.decrypt_markdown(contents)
        
        return {
            "success": True,
            "content": decrypted
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/encrypt")
async def encrypt_file(content: str = Form(...), key: str = Form(...)):
    if not key or not key.strip():
        raise HTTPException(status_code=422, detail="key 不能为空")
    try:
        from .encrypted_email import MarkdownEncryptor
        
        encryptor = MarkdownEncryptor(encryption_key=key)
        encrypted_data, method = encryptor.encrypt_markdown(content)
        
        return {
            "success": True,
            "encrypted_data": encrypted_data.hex(),
            "method": method
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
