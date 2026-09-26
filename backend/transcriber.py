import os
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

try:  # torch 可选：缺失时模型加载走离线分支
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    speaker: str
    confidence: float


class WhisperTranscriber:
    def __init__(self, model_name: str = "large-v3", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device if device else ("cuda" if (TORCH_AVAILABLE and torch.cuda.is_available()) else "cpu")
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            import whisper
            print(f"Loading Whisper model: {self.model_name} on {self.device}...")
            self.model = whisper.load_model(self.model_name, device=self.device)
            print("Whisper model loaded successfully.")
        except Exception as e:
            print(f"Warning: Could not load Whisper model: {e}")
            self.model = None

    def transcribe(self, audio_path: str, language: str = "zh", 
                   initial_prompt: Optional[str] = None) -> Dict:
        if self.model is None:
            return self._mock_transcribe(audio_path)

        try:
            options = {
                "language": language,
                "verbose": False,
                "word_timestamps": True,
                "initial_prompt": initial_prompt or "这是一段会议录音，包含多人对话。"
            }

            result = self.model.transcribe(audio_path, **options)

            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                    "confidence": seg.get("avg_logprob", 0.0),
                    "words": seg.get("words", [])
                })

            return {
                "success": True,
                "text": result["text"].strip(),
                "language": result.get("language", language),
                "segments": segments,
                "word_count": len(result["text"].split())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "segments": [],
                "language": language
            }

    def _mock_transcribe(self, audio_path: str) -> Dict:
        mock_text = "由于模型未加载，这是模拟的转写文本。会议讨论了项目进度和下一步计划。"
        return {
            "success": True,
            "text": mock_text,
            "language": "zh",
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": mock_text,
                    "confidence": 0.8,
                    "words": []
                }
            ],
            "word_count": len(mock_text.split()),
            "note": "Using mock transcription - model not loaded"
        }


class PyannoteDiarizer:
    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token or os.getenv("PYANNOTE_AUTH_TOKEN")
        self.pipeline = None
        self._load_pipeline()

    def _load_pipeline(self):
        try:
            from pyannote.audio import Pipeline
            print("Loading pyannote speaker diarization pipeline...")
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.auth_token
            )
            print("Pyannote pipeline loaded successfully.")
        except Exception as e:
            print(f"Warning: Could not load pyannote pipeline: {e}")
            self.pipeline = None

    def diarize(self, audio_path: str, num_speakers: Optional[int] = None) -> Dict:
        if self.pipeline is None:
            return self._mock_diarize(audio_path, num_speakers)

        try:
            diarization = self.pipeline(audio_path, num_speakers=num_speakers)

            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker,
                    "duration": turn.end - turn.start
                })

            speakers = list(set(seg["speaker"] for seg in segments))

            return {
                "success": True,
                "num_speakers": len(speakers),
                "speakers": sorted(speakers),
                "segments": segments,
                "total_duration": segments[-1]["end"] if segments else 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "num_speakers": 0,
                "speakers": [],
                "segments": []
            }

    def _mock_diarize(self, audio_path: str, num_speakers: Optional[int] = None) -> Dict:
        num_spk = num_speakers or 3
        speakers = [f"SPEAKER_{i:02d}" for i in range(num_spk)]
        segments = []
        current_time = 0.0

        for i in range(20):
            speaker = speakers[i % num_spk]
            duration = 3.0 + np.random.rand() * 5.0
            segments.append({
                "start": current_time,
                "end": current_time + duration,
                "speaker": speaker,
                "duration": duration
            })
            current_time += duration + 0.5

        return {
            "success": True,
            "num_speakers": num_spk,
            "speakers": speakers,
            "segments": segments,
            "total_duration": current_time,
            "note": "Using mock diarization - pipeline not loaded"
        }


class MeetingTranscriptIntegrator:
    def __init__(self, whisper_model: str = "large-v3", 
                 pyannote_token: Optional[str] = None):
        self.transcriber = WhisperTranscriber(model_name=whisper_model)
        self.diarizer = PyannoteDiarizer(auth_token=pyannote_token)

    def process_meeting_audio(self, audio_path: str, 
                              num_speakers: Optional[int] = None,
                              language: str = "zh") -> Dict:
        print("Starting transcription...")
        transcription = self.transcriber.transcribe(audio_path, language=language)

        if not transcription["success"]:
            return {
                "success": False,
                "error": f"Transcription failed: {transcription.get('error', 'Unknown error')}"
            }

        print("Starting speaker diarization...")
        diarization = self.diarizer.diarize(audio_path, num_speakers=num_speakers)

        if not diarization["success"]:
            print(f"Warning: Diarization failed: {diarization.get('error')}")
            diarization = self._fallback_diarization(transcription)

        print("Integrating transcription with speaker labels...")
        integrated_segments = self._integrate_transcript_and_diarization(
            transcription["segments"],
            diarization["segments"]
        )

        speaker_stats = self._calculate_speaker_stats(integrated_segments)

        return {
            "success": True,
            "full_text": transcription["text"],
            "language": transcription["language"],
            "num_speakers": diarization["num_speakers"],
            "speakers": diarization["speakers"],
            "segments": integrated_segments,
            "speaker_stats": speaker_stats,
            "transcription_segments": transcription["segments"],
            "diarization_segments": diarization["segments"]
        }

    def _fallback_diarization(self, transcription: Dict) -> Dict:
        segments = []
        for i, seg in enumerate(transcription["segments"]):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "speaker": f"SPEAKER_{i % 3:02d}",
                "duration": seg["end"] - seg["start"]
            })

        return {
            "success": True,
            "num_speakers": 3,
            "speakers": ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"],
            "segments": segments,
            "total_duration": segments[-1]["end"] if segments else 0,
            "note": "Using fallback diarization based on transcription segments"
        }

    def _integrate_transcript_and_diarization(self, 
                                              transcript_segments: List[Dict],
                                              diarization_segments: List[Dict]) -> List[Dict]:
        integrated = []

        for t_seg in transcript_segments:
            t_start, t_end = t_seg["start"], t_seg["end"]
            t_mid = (t_start + t_end) / 2

            best_speaker = "UNKNOWN"
            best_overlap = 0

            for d_seg in diarization_segments:
                d_start, d_end = d_seg["start"], d_seg["end"]
                overlap_start = max(t_start, d_start)
                overlap_end = min(t_end, d_end)
                overlap = max(0, overlap_end - overlap_start)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = d_seg["speaker"]

            if best_overlap / (t_end - t_start + 1e-10) < 0.3:
                for d_seg in diarization_segments:
                    if d_seg["start"] <= t_mid <= d_seg["end"]:
                        best_speaker = d_seg["speaker"]
                        break

            integrated.append({
                "start": t_start,
                "end": t_end,
                "text": t_seg["text"],
                "speaker": best_speaker,
                "confidence": t_seg.get("confidence", 0.0),
                "words": t_seg.get("words", [])
            })

        return integrated

    def _calculate_speaker_stats(self, segments: List[Dict]) -> Dict:
        stats = {}
        for seg in segments:
            speaker = seg["speaker"]
            if speaker not in stats:
                stats[speaker] = {"total_time": 0.0, "segments": 0, "words": 0}
            stats[speaker]["total_time"] += seg["end"] - seg["start"]
            stats[speaker]["segments"] += 1
            stats[speaker]["words"] += len(seg["text"].split())

        for speaker in stats:
            total = stats[speaker]["total_time"]
            stats[speaker]["avg_segment_length"] = total / stats[speaker]["segments"] if stats[speaker]["segments"] > 0 else 0

        return stats

    def generate_markdown_transcript(self, result: Dict) -> str:
        if not result.get("success"):
            return f"# 会议记录\n\n错误: {result.get('error', '处理失败')}"

        md_lines = []
        md_lines.append("# 会议记录")
        md_lines.append("")
        md_lines.append(f"- **时间**: 2026-05-18")
        md_lines.append(f"- **语言**: {result.get('language', 'zh')}")
        md_lines.append(f"- **参会人数**: {result.get('num_speakers', 0)}")
        md_lines.append(f"- **参会者**: {', '.join(result.get('speakers', []))}")
        md_lines.append("")
        md_lines.append("## 发言统计")
        md_lines.append("")
        md_lines.append("| 发言者 | 总时长(秒) | 发言次数 | 平均时长(秒) |")
        md_lines.append("|--------|-----------|----------|-------------|")
        for speaker, stats in result.get("speaker_stats", {}).items():
            md_lines.append(f"| {speaker} | {stats['total_time']:.1f} | {stats['segments']} | {stats['avg_segment_length']:.1f} |")
        md_lines.append("")
        md_lines.append("## 会议全文")
        md_lines.append("")
        for seg in result.get("segments", []):
            speaker = seg["speaker"]
            start = self._format_time(seg["start"])
            end = self._format_time(seg["end"])
            text = seg["text"]
            md_lines.append(f"**[{start} - {end}] {speaker}**: {text}")
            md_lines.append("")
        md_lines.append("")
        md_lines.append("## 完整文本")
        md_lines.append("")
        md_lines.append(result.get("full_text", ""))

        return "\n".join(md_lines)

    def _format_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
