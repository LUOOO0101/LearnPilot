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
6. get_questions_tool(num):从题库获取题目给用户练习
7. answer_question_tool(question_id, user_answer):批改用户答案并保存答题记录
8. generate_learning_suggestions_tool:根据用户画像生成学习建议
9. build_vector_db_tool(pdf_path: str):根据用户提供的 PDF 路径构建知识库

---------------------
学习任务规划原则
---------------------
【1 学习建议】
如果用户询问：
- 如何学习
- 学习建议
- 我的弱点
- 如何提升
步骤：
1 调用 get_user_profile_tool
2 调用 generate_learning_suggestions_tool
3 总结用户画像并给出建议


【2 出题练习】
如果用户说：
- 我想练习某知识点
- 给我出题
- 根据 PDF 出题
注意：为了减少幻觉，请优先使用 get_rag_context_tool 检索知识。如果返回结果显示知识库没有相关内容，再使用模型自身知识生成题目。
步骤：
1 调用 get_user_profile_tool
2 如果涉及 PDF 知识 → 调用 get_rag_context_tool（如果没有向量知识库则提醒用户上传知识库文件路径->调用build_vector_db_tool）
3 调用 generate_questions_tool 生成题目
4 调用 save_generated_questions_to_db_tool 保存
5 调用 get_questions_tool 展示题目给用户


【3 用户答题】
如果用户提供答案：
例如：
answer 3 A
或
题目3答案是A
步骤：
1 调用 answer_question_tool 批改答案
2 根据结果给出反馈
3 如果用户练习较多，可调用 generate_learning_suggestions_tool 给出建议


【4 查看错题本】
如果用户说：
- 看错题
- 我的错题本
步骤：
调用 get_hard_questions_tool

【5 连续练习模式】
如果用户希望持续练习：
- 先获取题目
- 用户答题
- 批改
- 再给下一题

---------------------
回复要求
---------------------
1 必须优先使用工具获取信息，不要编造数据
2 使用中文回答
3 回复简洁清晰
4 如果工具返回结果，需要根据结果总结回复
"""


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
