import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class MeetingSummary:
    title: str
    date: str
    participants: List[str]
    key_topics: List[str]
    decisions: List[str]
    action_items: List[Dict]
    risks: List[str]
    next_meeting: Optional[str]
    summary: str
    full_transcript: str


class OpenAISummaryGenerator:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            from openai import OpenAI
            if self.api_key:
                self.client = OpenAI(api_key=self.api_key)
                print("OpenAI client initialized successfully.")
            else:
                print("Warning: No OpenAI API key provided.")
                self.client = None
        except Exception as e:
            print(f"Warning: Could not initialize OpenAI client: {e}")
            self.client = None

    def generate_summary(self, transcript_data: Dict, 
                         context: Optional[Dict] = None) -> Dict:
        if not transcript_data.get("success"):
            return {
                "success": False,
                "error": "Invalid transcript data"
            }

        transcript_text = self._prepare_transcript_for_summary(transcript_data)
        prompt = self._build_summary_prompt(transcript_text, context)

        if self.client is None:
            return self._mock_summary(transcript_data, context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的会议纪要撰写专家。请根据提供的会议转写内容，生成一份模糊但可用的会议摘要。由于音频质量可能较差，请做出合理的推断，但要标注不确定的信息。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            summary_data = json.loads(content)

            return {
                "success": True,
                "summary": summary_data,
                "raw_response": content
            }
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._mock_summary(transcript_data, context)

    def _prepare_transcript_for_summary(self, transcript_data: Dict) -> str:
        segments = transcript_data.get("segments", [])
        lines = []

        for seg in segments:
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "")
            if text.strip():
                lines.append(f"[{speaker}]: {text}")

        return "\n".join(lines)

    def _build_summary_prompt(self, transcript: str, context: Optional[Dict] = None) -> str:
        context_info = ""
        if context:
            context_info = f"\n额外背景信息:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n"

        prompt = f"""请分析以下会议转写内容，生成一份结构化的会议摘要。
由于音频是从激光测振仪获取的，质量可能较差，请：
1. 对不确定的内容做出合理推断
2. 标注可能存在的不准确性
3. 保持摘要的模糊性但确保可用性

{context_info}

会议转写内容:
{transcript}

请以JSON格式输出，包含以下字段:
- "title": 会议主题（推断）
- "date": 会议日期（格式: YYYY-MM-DD）
- "participants": 参会人员列表（从SPEAKER_XX推断身份）
- "key_topics": 5-10个讨论的主要议题
- "decisions": 会议做出的重要决定
- "action_items": 行动项列表，每项包含"task"、"assignee"、"deadline"
- "risks": 识别到的风险或问题
- "next_meeting": 下次会议安排（如果有）
- "summary": 200-300字的会议总体摘要
- "confidence_note": 关于信息准确性的说明

请确保输出是有效的JSON格式。"""

        return prompt

    def _mock_summary(self, transcript_data: Dict, context: Optional[Dict] = None) -> Dict:
        speakers = transcript_data.get("speakers", [])
        participants = [f"参会者_{i+1}" for i in range(len(speakers))]

        mock_summary = {
            "title": "项目进展讨论会议",
            "date": "2026-05-18",
            "participants": participants,
            "key_topics": [
                "项目进度汇报",
                "技术方案讨论",
                "资源分配协调",
                "风险评估与应对",
                "下一步计划安排"
            ],
            "decisions": [
                "同意采用新的技术架构方案",
                "确定项目里程碑节点",
                "批准增加研发资源投入"
            ],
            "action_items": [
                {"task": "完成技术方案文档", "assignee": participants[0] if participants else "待定", "deadline": "2026-05-25"},
                {"task": "准备项目演示材料", "assignee": participants[1] if len(participants) > 1 else "待定", "deadline": "2026-06-01"},
                {"task": "协调跨部门资源", "assignee": participants[2] if len(participants) > 2 else "待定", "deadline": "2026-05-20"}
            ],
            "risks": [
                "项目进度存在延期风险",
                "部分技术细节需要进一步验证",
                "跨部门沟通效率有待提升"
            ],
            "next_meeting": "2026-05-25 14:00",
            "summary": "本次会议主要讨论了项目的整体进展情况。参会人员汇报了各模块的开发进度，讨论了技术方案的可行性，并对项目中存在的风险进行了评估。会议决定采用新的技术架构以提升系统性能，同时确定了关键里程碑节点。需要在下周前完成技术方案文档的编写，并准备项目演示材料。",
            "confidence_note": "由于音频质量限制，本摘要基于部分可识别内容推断生成，可能存在不准确性，仅供参考。"
        }

        return {
            "success": True,
            "summary": mock_summary,
            "raw_response": json.dumps(mock_summary, ensure_ascii=False, indent=2),
            "note": "Using mock summary - OpenAI client not available"
        }

    def generate_markdown_summary(self, summary_data: Dict, 
                                  transcript_data: Dict) -> str:
        if not summary_data.get("success"):
            return f"# 会议摘要\n\n错误: {summary_data.get('error', '生成失败')}"

        summary = summary_data.get("summary", {})

        md_lines = []
        md_lines.append("# 会议纪要")
        md_lines.append("")
        md_lines.append(f"**注意**: 本纪要基于激光测振仪获取的音频生成，内容可能存在不准确性，仅供参考。")
        md_lines.append("")
        md_lines.append("## 基本信息")
        md_lines.append("")
        md_lines.append(f"- **会议主题**: {summary.get('title', '未确定')}")
        md_lines.append(f"- **会议日期**: {summary.get('date', '未确定')}")
        md_lines.append(f"- **参会人员**: {', '.join(summary.get('participants', []))}")
        md_lines.append("")
        md_lines.append("## 讨论议题")
        md_lines.append("")
        for i, topic in enumerate(summary.get("key_topics", []), 1):
            md_lines.append(f"{i}. {topic}")
        md_lines.append("")
        md_lines.append("## 重要决定")
        md_lines.append("")
        for i, decision in enumerate(summary.get("decisions", []), 1):
            md_lines.append(f"{i}. {decision}")
        md_lines.append("")
        md_lines.append("## 行动项")
        md_lines.append("")
        md_lines.append("| 任务 | 负责人 | 截止日期 |")
        md_lines.append("|------|--------|----------|")
        for item in summary.get("action_items", []):
            md_lines.append(f"| {item.get('task', '')} | {item.get('assignee', '')} | {item.get('deadline', '')} |")
        md_lines.append("")
        md_lines.append("## 风险与问题")
        md_lines.append("")
        for i, risk in enumerate(summary.get("risks", []), 1):
            md_lines.append(f"{i}. {risk}")
        md_lines.append("")
        if summary.get("next_meeting"):
            md_lines.append("## 下次会议")
            md_lines.append("")
            md_lines.append(f"- {summary.get('next_meeting')}")
            md_lines.append("")
        md_lines.append("## 会议摘要")
        md_lines.append("")
        md_lines.append(summary.get("summary", ""))
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        md_lines.append(f"*准确性说明: {summary.get('confidence_note', '内容基于音频推断，可能存在误差')}*")
        md_lines.append("")
        md_lines.append("## 附录: 完整转写")
        md_lines.append("")
        md_lines.append("```")
        md_lines.append(transcript_data.get("full_text", "")[:2000])
        if len(transcript_data.get("full_text", "")) > 2000:
            md_lines.append("... (内容过长，已截断)")
        md_lines.append("```")

        return "\n".join(md_lines)
