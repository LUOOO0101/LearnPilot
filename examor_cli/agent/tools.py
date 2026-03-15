"""LangChain tools for the learning agent.

Tools 与直接调函数的区别：
- 直接调用：代码里固定顺序（先 A 再 B 再 C），逻辑写死。
- Tools：把能力暴露成「工具」，由 Agent（LLM）根据用户意图决定调用哪个、什么顺序、
  是否多步（如先查画像再出题再给建议）。便于扩展、且 Agent 可以自主规划。

本模块将 get_user_profile、RAG 检索、出题、保存、生成学习建议等封装成工具，
供 learning_agent 在 ReAct 循环中按需调用。
"""

from __future__ import annotations

import json
from typing import Any, List, Optional

from langchain_core.tools import tool

from examor_cli.config import LLM_CONFIG
from examor_cli.core import generate_questions_with_format_check
from examor_cli.db import save_question_to_db
from examor_cli.memory import get_user_profile, DEFAULT_USER_ID
from examor_cli.rag import PDFRAG

# 供 save_generated_questions_to_db 使用：上次 generate 的结果
_last_generated_questions: List[dict] = []


def _format_profile(profile: dict) -> str:
    """将 get_user_profile 返回的 dict 格式化为 Agent 可读的字符串。"""
    weak = profile.get("weak_types", [])
    hard = profile.get("hard_questions", [])
    type_perf = profile.get("type_perf", {})
    lines = [
        "【用户画像摘要】",
        f"弱项题型（正确率<60%且作答≥3）：{weak or '无'}",
        f"易错题数量：{len(hard)}",
    ]
    for t, stats in type_perf.items():
        acc = stats.get("accuracy", 0)
        total = stats.get("total", 0)
        lines.append(f"  - {t}: 作答{total}次，正确率 {acc*100:.0f}%")
    if hard:
        lines.append("易错题（前5条）：")
        for h in hard[:5]:
            lines.append(
                f"  ID{h['question_id']} {h['type']} 正确率{h['accuracy']*100:.0f}% "
                f"{h['content'][:50]}..."
            )
    return "\n".join(lines)


@tool
def get_user_profile_tool() -> str:
    """获取当前用户的长期学习画像（弱项题型、易错题、各题型正确率）。在给出学习建议或出题前应先调用此工具了解用户情况。"""
    profile = get_user_profile(DEFAULT_USER_ID)
    return _format_profile(profile)


@tool
def get_hard_questions_tool() -> str:
    """获取用户的易错题列表（错题本）：作答次数≥3且正确率<60%的题目。用于提醒用户重点练习或出题时优先覆盖这些知识点。"""
    profile = get_user_profile(DEFAULT_USER_ID)
    hard = profile.get("hard_questions", [])
    if not hard:
        return "当前没有符合条件的易错题。"
    lines = [f"共 {len(hard)} 道易错题："]
    for h in hard[:15]:
        lines.append(
            f"  ID{h['question_id']} | {h['type']} | 作答{h['total_attempts']}次 "
            f"正确率{h['accuracy']*100:.0f}% | {h['content'][:60]}..."
        )
    return "\n".join(lines)


@tool
def get_rag_context_tool(query: str) -> str:
    """从 PDF 知识库中检索与 query 相关的上下文。在基于 PDF 出题前需先调用此工具获取知识内容。query 为用户想考察的知识点或主题。"""
    if not query or not query.strip():
        return "请提供非空的检索内容（知识点或主题）。"
    try:
        rag = PDFRAG()
        return rag.retrieve(query.strip(), k=5)
    except Exception as e:
        return f"RAG 检索失败：{e}。请确认已运行 build-vector-db 构建过向量库。"


@tool
def generate_questions_tool(
    note_content: str,
    num: int = 5,
    question_types: str = "single_choice,short_answer",
) -> str:
    """根据笔记/知识内容生成考题。note_content 为出题依据的文本；num 为题目数量；question_types 为题型，逗号分隔，如 single_choice,short_answer,fill_blank。生成后需调用 save_generated_questions_to_db 才会写入题库。"""
    global _last_generated_questions
    types_list = [t.strip() for t in question_types.split(",")]
    try:
        questions = generate_questions_with_format_check(
            note_content=note_content, num=num, question_types=types_list
        )
    except Exception as e:
        _last_generated_questions = []
        return f"生成考题失败：{e}"
    if not questions:
        _last_generated_questions = []
        return "未生成任何题目。"
    _last_generated_questions = questions
    summary = f"已生成 {len(questions)} 道题，题型：{types_list}。请调用 save_generated_questions_to_db 保存到题库。"
    return summary


@tool
def save_generated_questions_to_db_tool() -> str:
    """将最近一次 generate_questions_tool 生成的题目保存到数据库。若尚未生成过题目则无效果。"""
    global _last_generated_questions
    if not _last_generated_questions:
        return "当前没有待保存的题目，请先使用 generate_questions_tool 生成考题。"
    try:
        save_question_to_db(_last_generated_questions)
        n = len(_last_generated_questions)
        _last_generated_questions = []
        return f"已成功将 {n} 道题保存到题库。"
    except Exception as e:
        return f"保存失败：{e}"


def _generate_learning_suggestions_impl() -> str:
    """根据用户画像调用 LLM 生成学习建议（纯逻辑，供 tool 与普通调用复用）。"""
    from langchain_openai import ChatOpenAI

    profile = get_user_profile(DEFAULT_USER_ID)
    profile_text = _format_profile(profile)
    weak = profile.get("weak_types", [])
    hard = profile.get("hard_questions", [])

    if not weak and not hard:
        return "当前暂无足够答题数据，无法生成针对性学习建议。建议先完成一些题目后再查看建议。"

    prompt = f"""根据以下用户学习画像，用 2～4 条简短、可执行的学习建议回复，帮助用户提升效率。不要泛泛而谈，要结合其弱项题型和易错题情况。

用户画像：
{profile_text}

请直接输出建议，不要输出「建议：」等前缀，每条一行或分点即可。"""

    llm = ChatOpenAI(
        api_key=LLM_CONFIG["api_key"],
        base_url=LLM_CONFIG["base_url"],
        model_name=LLM_CONFIG["model"],
        temperature=0.3,
    )
    try:
        res = llm.invoke(prompt)
        return (res.content or "").strip() or "暂时无法生成建议。"
    except Exception as e:
        return f"生成学习建议时出错：{e}"


@tool
def generate_learning_suggestions_tool() -> str:
    """根据用户当前的学习画像（弱项题型、易错题、正确率）生成简短可执行的学习建议。建议在用户询问如何提升或完成一批练习后调用。"""
    return _generate_learning_suggestions_impl()


def get_all_agent_tools() -> list:
    """返回供 Agent 使用的全部工具列表。"""
    return [
        get_user_profile_tool,
        get_hard_questions_tool,
        get_rag_context_tool,
        generate_questions_tool,
        save_generated_questions_to_db_tool,
        generate_learning_suggestions_tool,
    ]


__all__ = [
    "get_user_profile_tool",
    "get_hard_questions_tool",
    "get_rag_context_tool",
    "generate_questions_tool",
    "save_generated_questions_to_db_tool",
    "generate_learning_suggestions_tool",
    "get_all_agent_tools",
    "_generate_learning_suggestions_impl",
]
