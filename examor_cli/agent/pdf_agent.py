"""Agent that uses PDF-based RAG and core generation to create questions."""

import json

from rich.console import Console
from langchain_openai import ChatOpenAI

from examor_cli.config import LLM_CONFIG
from examor_cli.core import generate_questions_with_format_check
from examor_cli.db import save_question_to_db
from examor_cli.rag import PDFRAG
from examor_cli.memory import get_user_profile, DEFAULT_USER_ID, session_memory

console = Console()


class PDFExamAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
            model_name=LLM_CONFIG["model"],
            temperature=0.3,
        )

    def analyze_with_rag(self, user_query):
        """Agent 第一步：通过 RAG 获取知识，分析笔记内容"""
        rag = PDFRAG()
        knowledge = rag.retrieve(user_query)

        prompt = f"""
        严格按照以下要求输出，只返回 JSON 字符串，不要加任何额外内容（如解释、换行、符号）：
        基于用户查询：{user_query}
        相关知识库内容：
        {knowledge}

        请分析以下内容：
        1. 该知识点的难度（简单/中等/困难）
        2. 核心知识点（列出3-5个）
        3. 建议生成的题目数量（3-10道）
        4. 建议题型（single_choice/short_answer/fill_blank）

        输出 JSON 格式（必须是标准 JSON，无多余内容）：
        {{
            "difficulty": "",
            "core_knowledge": [],
            "suggested_num": 5,
            "suggested_types": ["single_choice"]
        }}
        """

        max_retry = 3
        for retry in range(max_retry):
            try:
                res = self.llm.invoke(prompt)
                res_content = res.content.strip()
                if not res_content:
                    raise Exception("LLM 返回内容为空")
                analysis = json.loads(res_content)
                return analysis, knowledge
            except (json.JSONDecodeError, Exception) as e:
                console.print(
                    f"[yellow]⚠️  第 {retry + 1} 次解析失败：{e}，重试中...[/yellow]"
                )
                continue

        console.print("[red]❌ LLM 分析失败，使用默认配置[/red]")
        default_analysis = {
            "difficulty": "中等",
            "core_knowledge": [user_query],
            "suggested_num": 3,
            "suggested_types": ["single_choice"],
        }
        return default_analysis, knowledge

    def generate_agent_questions(self, user_query):
        """Agent 完整流程：分析 → RAG → 生成考题 → 纠错"""
        console.print("[blue]🤖 Agent 正在分析用户需求...[/blue]")
        analysis, knowledge = self.analyze_with_rag(user_query)

        # 读取长期记忆画像（弱项题型 / 易错题等）
        profile = get_user_profile(DEFAULT_USER_ID)
        weak_types = profile.get("weak_types", [])
        hard_questions = profile.get("hard_questions", [])

        # 更新短期记忆中的偏好（示例：优先使用建议的题型）
        session_memory.update_preferences(
            preferred_types=analysis.get("suggested_types", []),
            preferred_difficulty=analysis.get("difficulty", "中等"),
        )

        console.print(f"[green]✅ 分析结果：{analysis}[/green]")

        enhanced_note = f"""
        基于以下知识生成考题：
        用户查询：{user_query}
        知识库补充知识：
        {knowledge}

        要求：
        - 难度：{analysis['difficulty']}
        - 覆盖核心知识点：{analysis['core_knowledge']}
        - 生成 {analysis['suggested_num']} 道题
        - 题型：{analysis['suggested_types']}
        - 历史弱项题型（可适当增加比例）：{weak_types}
        - 历史易错题（请优先覆盖这些题目的考察点，不要直接重复原题）：
        """

        if hard_questions:
            top_hard = hard_questions[:5]
            for h in top_hard:
                content = h["content"]
                short = content[:40] + "..." if len(content) > 40 else content
                acc = int(h["accuracy"] * 100) if h["accuracy"] is not None else 0
                enhanced_note += f"- 题ID {h['question_id']}，题型 {h['type']}，历史正确率约 {acc}%：{short}\n"

        enhanced_note += """
        - 输出标准 JSON（带 options）
        """

        console.print("[blue]🤖 正在生成考题...[/blue]")
        questions = generate_questions_with_format_check(
            note_content=enhanced_note,
            num=analysis["suggested_num"],
            question_types=analysis["suggested_types"],
        )

        save_question_to_db(questions)
        console.print(f"✅ Agent 任务完成：生成 {len(questions)} 道考题")
        return questions


__all__ = [
    "PDFExamAgent",
]

