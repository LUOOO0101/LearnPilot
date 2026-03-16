"""基于 Tools 的智能学习助手 Agent。

与线性 PDFExamAgent 的区别：
- 线性：固定流程 RAG → 分析 → 出题 → 保存，无法根据用户意图规划。
- 本 Agent：通过 LangChain Tools 暴露能力，由 LLM 在对话中决定调用哪些工具、顺序如何，
  可先查用户画像 → 生成学习建议 → 再根据用户需求决定是否从 PDF 检索、出题、保存等，
  实现「主动分析用户画像并给出学习建议」的规划能力。
"""

from __future__ import annotations

import json as _json
from typing import Any, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from rich.console import Console

from examor_cli.config import LLM_CONFIG
from examor_cli.agent.tools import get_all_agent_tools

console = Console()

# 工具列表：与 bind_tools 和 _run_tool 共用
_TOOLS_LIST = get_all_agent_tools()


SYSTEM_PROMPT = """你是一位学习助手 Agent，负责根据用户需求规划并调用工具，帮助用户提升学习效率。

你可用的工具：
1. get_user_profile_tool：获取用户学习画像（弱项题型、易错题、各题型正确率）。
2. get_hard_questions_tool：获取易错题列表（错题本）。
3. get_rag_context_tool(query)：从 PDF 知识库检索与 query 相关的知识内容。
4. generate_questions_tool(note_content, num, question_types)：根据知识内容生成考题（生成后需再调用保存工具才会入库）。
5. save_generated_questions_to_db_tool：将最近生成的题目保存到题库。
6. generate_learning_suggestions_tool：根据用户画像生成简短可执行的学习建议。

规划与执行原则：
- 当用户询问「学习建议」「怎么提升」「我哪里薄弱」时：先调用 get_user_profile_tool 了解情况，再调用 generate_learning_suggestions_tool 给出建议，并可用 1～2 句话总结画像与建议。
- 当用户希望「根据某知识点出题」或「从 PDF 出题」时：先 get_user_profile_tool 了解薄弱点，若涉及 PDF 则先 get_rag_context_tool(用户知识点)，再 generate_questions_tool（把检索到的知识 + 用户薄弱点写进 note_content），最后 save_generated_questions_to_db_tool；并在结束时视情况简要给出学习建议或鼓励。
- 当用户仅想「看看我的错题本」时：调用 get_hard_questions_tool 并整理后回复。
- 主动思考：在适当时机（例如用户完成一批练习或询问进度时）主动调用 get_user_profile_tool 与 generate_learning_suggestions_tool，输出用户画像摘要与学习建议，提升学习效率。

请用中文回复用户；若调用了工具，根据工具返回内容组织你的回复，不要编造工具未返回的信息。"""


def _run_tool(name: str, args: dict) -> str:

    tools_by_name = {t.name: t for t in _TOOLS_LIST}

    tool = tools_by_name.get(name)

    if not tool:
        return f"未知工具：{name}"

    try:
        return str(tool.invoke(args or {}))
    except Exception as e:
        return f"工具执行出错：{e}"


# def run_learning_agent(user_input: str, max_steps: int = 10) -> str:
#     """运行学习助手 Agent：根据用户输入规划并调用 tools，返回最终回复。
#
#     使用 LLM bind_tools 进行多轮：每轮若模型返回 tool_calls 则执行并追加结果后继续，
#     直到模型不再调用工具或达到 max_steps。
#     """
#     llm = ChatOpenAI(
#         api_key=LLM_CONFIG["api_key"],
#         base_url=LLM_CONFIG["base_url"],
#         model_name=LLM_CONFIG["model"],
#         temperature=0.3,
#     ).bind_tools(_TOOLS_LIST)
#
#     messages: List[Any] = [
#         SystemMessage(content=SYSTEM_PROMPT),
#         HumanMessage(content=user_input),
#     ]
#
#     for step in range(max_steps):
#
#         response = llm.invoke(messages)
#
#         if not response.tool_calls:
#             return (response.content or "").strip()
#
#         # 先 append assistant
#         messages.append(response)
#
#         for tc in response.tool_calls:
#             name = tc["name"]
#             args = tc.get("args", {})
#             tid = tc["id"]
#
#             result = _run_tool(name, args)
#
#             messages.append(
#                 ToolMessage(
#                     content=result,
#                     tool_call_id=tid
#                 )
#             )
#
#     return "已达到最大步数，请简化需求后重试。"

def run_learning_agent(
    user_input: str,
    history: List[tuple] | None = None,
    max_steps: int = 10,
) -> str:

    llm = ChatOpenAI(
        api_key=LLM_CONFIG["api_key"],
        base_url=LLM_CONFIG["base_url"],
        model_name=LLM_CONFIG["model"],
        temperature=0.3,
    ).bind_tools(_TOOLS_LIST)

    messages: List[Any] = [
        SystemMessage(content=SYSTEM_PROMPT)
    ]

    # 加载历史（只取最近几轮）
    if history:
        for role, content in history[-6:]:
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_input))

    final_answer = ""

    for step in range(max_steps):

        response = llm.invoke(messages)

        # 没有tool调用
        if not response.tool_calls:

            final_answer = (response.content or "").strip()

            return final_answer

        messages.append(response)

        for tc in response.tool_calls:

            name = tc["name"]
            args = tc.get("args", {})
            tid = tc["id"]

            result = _run_tool(name, args)

            messages.append(
                ToolMessage(
                    content=result,
                    tool_call_id=tid
                )
            )

    return "已达到最大步数，请简化需求后重试。"
__all__ = ["run_learning_agent", "SYSTEM_PROMPT"]
