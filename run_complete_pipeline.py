#!/usr/bin/env python3
"""
激光测振会议系统 - 完整处理流程示例
Laser Vibrometry Spy System - Complete Pipeline Example

警告: 本系统仅用于合法授权的安全测试目的。
Warning: This system is for authorized security testing purposes only.
"""

import os
import sys
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.audio_processor import LaserAudioProcessor
from backend.transcriber import MeetingTranscriptIntegrator
from backend.summary_generator import OpenAISummaryGenerator
from backend.encrypted_email import MeetingMinutesDispatcher


def generate_sample_vibration_data(duration: int = 30, sample_rate: int = 48000) -> str:
    """生成模拟的激光振动数据用于测试"""
    print("Generating sample vibration data...")
    
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    speech_like = np.zeros_like(t)
    for freq in [100, 200, 300, 500, 800]:
        speech_like += np.sin(2 * np.pi * freq * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.5 * t))
    
    noise = np.random.randn(len(t)) * 0.8
    echo = np.zeros_like(t)
    echo[:-int(0.1 * sample_rate)] = speech_like[int(0.1 * sample_rate):] * 0.3
    
    vibration_data = speech_like + noise + echo
    vibration_data = vibration_data / np.max(np.abs(vibration_data))
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    sf.write(temp_file.name, vibration_data, sample_rate)
    print(f"Sample data saved to: {temp_file.name}")
    
    return temp_file.name


def process_complete_pipeline(input_audio_path: str, 
                              num_speakers: int = 3,
                              language: str = "zh",
                              recipient_emails: list = None,
                              output_dir: str = "./output") -> dict:
    """执行完整的处理流程"""
    
    print("\n" + "="*70)
    print("LASER VIBROMETRY SPY SYSTEM - COMPLETE PROCESSING PIPELINE")
    print("="*70)
    
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    
    print(f"\n[Step 1/7] Audio Enhancement & Deconvolution...")
    processor = LaserAudioProcessor()
    enhanced_audio, enhanced_path = processor.process_audio_file(
        input_audio_path,
        output_path=os.path.join(output_dir, "enhanced_audio.wav")
    )
    print(f"  Enhanced audio saved to: {enhanced_path}")
    results["enhanced_audio"] = enhanced_path
    
    print(f"\n[Step 2/7] Speech Transcription & Speaker Diarization...")
    integrator = MeetingTranscriptIntegrator()
    transcript_result = integrator.process_meeting_audio(
        enhanced_path,
        num_speakers=num_speakers,
        language=language
    )
    
    if not transcript_result["success"]:
        print(f"  ERROR: Transcription failed: {transcript_result.get('error')}")
        return results
    
    print(f"  Transcribed {len(transcript_result['segments'])} segments")
    print(f"  Detected {transcript_result['num_speakers']} speakers")
    results["transcript"] = transcript_result
    
    markdown_transcript = integrator.generate_markdown_transcript(transcript_result)
    transcript_md_path = os.path.join(output_dir, "transcript.md")
    with open(transcript_md_path, 'w', encoding='utf-8') as f:
        f.write(markdown_transcript)
    print(f"  Transcript Markdown saved to: {transcript_md_path}")
    results["markdown_transcript"] = transcript_md_path
    
    print(f"\n[Step 3/7] AI Summary Generation...")
    try:
        summary_gen = OpenAISummaryGenerator()
        summary_result = summary_gen.generate_summary(transcript_result)
        
        if summary_result["success"]:
            print(f"  Summary generated successfully")
            results["summary"] = summary_result
            
            markdown_summary = summary_gen.generate_markdown_summary(summary_result, transcript_result)
            summary_md_path = os.path.join(output_dir, "meeting_summary.md")
            with open(summary_md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_summary)
            print(f"  Summary Markdown saved to: {summary_md_path}")
            results["markdown_summary"] = summary_md_path
        else:
            print(f"  Warning: Summary generation failed: {summary_result.get('error')}")
            print("  Using transcript only for output")
            results["summary"] = None
    except Exception as e:
        print(f"  Warning: Summary generation error: {e}")
        results["summary"] = None
    
    print(f"\n[Step 4/7] Encryption & Email Dispatch...")
    dispatcher = MeetingMinutesDispatcher()
    
    if recipient_emails and results.get("markdown_summary"):
        email_result = dispatcher.generate_and_dispatch(
            markdown_content=results["markdown_summary"],
            to_emails=recipient_emails,
            output_dir=output_dir,
            send_email=False
        )
        print(f"  Encrypted file saved to: {email_result.get('local_path')}")
        results["encrypted_file"] = email_result.get('local_path')
    elif results.get("markdown_summary"):
        from backend.encrypted_email import MarkdownEncryptor
        encryptor = MarkdownEncryptor()
        with open(results["markdown_summary"], 'r', encoding='utf-8') as f:
            content = f.read()
        encrypted_path = os.path.join(output_dir, "meeting_minutes_encrypted.bin")
        enc_result = encryptor.save_encrypted_file(content, encrypted_path)
        if enc_result["success"]:
            print(f"  Encrypted file saved to: {encrypted_path}")
            results["encrypted_file"] = encrypted_path
    
    print("\n" + "="*70)
    print("PROCESSING COMPLETE")
    print("="*70)
    print(f"\nOutput directory: {os.path.abspath(output_dir)}")
    print("\nGenerated files:")
    for key, path in results.items():
        if isinstance(path, str) and os.path.exists(path):
            print(f"  - {key}: {os.path.basename(path)}")
    
    return results


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║           LASER VIBROMETRY SPY SYSTEM                             ║
║           激光测振远程声波获取系统                                ║
╠═══════════════════════════════════════════════════════════════════╣
║  WARNING: This system is for authorized security testing only.   ║
║  警告: 本系统仅用于合法授权的安全测试目的。                       ║
║  Unauthorized use may violate privacy laws.                      ║
║  未经授权的使用可能违反隐私法律。                                 ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    import argparse
    parser = argparse.ArgumentParser(description="Laser Vibrometry Spy System - Complete Pipeline")
    parser.add_argument("--input", "-i", type=str, help="Input audio file path")
    parser.add_argument("--num-speakers", "-n", type=int, default=3, help="Number of expected speakers")
    parser.add_argument("--language", "-l", type=str, default="zh", help="Language code (zh, en)")
    parser.add_argument("--output", "-o", type=str, default="./output", help="Output directory")
    parser.add_argument("--emails", nargs="*", help="Recipient email addresses")
    parser.add_argument("--sample", action="store_true", help="Generate and use sample data")
    
    args = parser.parse_args()
    
    if args.sample:
        input_path = generate_sample_vibration_data(duration=60)
    elif args.input:
        input_path = args.input
        if not os.path.exists(input_path):
            print(f"ERROR: Input file not found: {input_path}")
            sys.exit(1)
    else:
        print("No input specified. Using sample data for demonstration...")
        input_path = generate_sample_vibration_data(duration=60)
    
    try:
        results = process_complete_pipeline(
            input_audio_path=input_path,
            num_speakers=args.num_speakers,
            language=args.language,
            recipient_emails=args.emails,
            output_dir=args.output
        )
        
        print("\n" + "="*70)
        print("DEMONSTRATION COMPLETE")
        print("="*70)
        print("\nTo start the web interface:")
        print("  1. Run: start_backend.bat")
        print("  2. Run: start_frontend.bat")
        print("  3. Open: http://localhost:5173")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
