"""Answer evaluation logic for Examor CLI."""

import json
from langchain_openai import ChatOpenAI
from rich.console import Console

from examor_cli.config import LLM_CONFIG

console = Console()


def evaluate_answer(question_content, user_answer, correct_answer):
    """AI 批改答案（兼容 LLM 返回的 Markdown 格式）"""
    console.print("[blue]🤖 正在批改答案...[/blue]")

    prompt = f"""
    请批改以下答题结果，严格按照以下要求输出：
    1. 仅返回标准 JSON 字符串，不要加 ```json、注释、换行等任何额外内容；
    2. score 为 0-100 的整数（完全正确 100，部分正确 50，错误 0）；
    3. feedback 为详细的批改说明，包含错误原因和正确解析。

    题目内容：{question_content}
    用户答案：{user_answer}
    正确答案：{correct_answer}

    输出示例（仅返回 JSON）：
    {{"score": 100, "feedback": "答案正确，解析：..."}}
    """

    try:
        llm = ChatOpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
            model_name=LLM_CONFIG["model"],
            temperature=0.1,
        )
        res = llm.invoke(prompt)
        res_content = res.content.strip()

        if res_content.startswith("```json"):
            res_content = res_content.replace("```json", "").replace("```", "").strip()
        elif res_content.startswith("```"):
            res_content = res_content.replace("```", "").strip()

        result = json.loads(res_content)
        score = result.get("score", 0)
        feedback = result.get("feedback", "无批改反馈")

        return score, feedback
    except json.JSONDecodeError:
        console.print(f"[red]❌ LLM 返回非标准 JSON 格式：{res_content}[/red]")
        if user_answer.strip().lower() == correct_answer.strip().lower():
            return 100, "答案正确（LLM 格式错误，手动校验）"
        return 0, f"答案错误（LLM 格式错误，手动校验）。正确答案：{correct_answer}"
    except Exception as e:
        console.print(f"[red]❌ 批改失败：{str(e)}[/red]")
        return 0, f"批改失败：{str(e)}"


__all__ = [
    "evaluate_answer",
]

