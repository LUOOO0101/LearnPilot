"""Question generation logic for Examor CLI."""

import json
import re
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from rich.console import Console

from examor_cli.config import LLM_CONFIG, SUPPORTED_TYPES, SINGLE_CHOICE_OPTION_NUM

console = Console()

llm = ChatOpenAI(
    api_key=LLM_CONFIG["api_key"],
    base_url=LLM_CONFIG["base_url"],
    model_name=LLM_CONFIG["model"],
    temperature=LLM_CONFIG["temperature"],
)


def _normalize_text(text: str) -> str:
    """Normalize question text for simple similarity / duplicate checks."""
    s = text.lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[，。,\.!！？:：;；？]", "", s)
    return s


def _dedupe_questions_basic(questions):
    """Remove obviously duplicated / near-identical questions within one batch.

    - 同一批里，题干在去掉空格和常见标点后完全相同的，只保留第一道。
    - 这样可以避免“同一知识点几乎相同问法”在一批里成对出现。
    """
    seen = set()
    result = []
    for q in questions:
        content = str(q.get("content", ""))
        norm = _normalize_text(content)
        if norm in seen:
            continue
        seen.add(norm)
        result.append(q)
    return result


def generate_questions(note_content, question_num=5, question_types=None):
    """Generate questions from note content."""
    if not note_content.strip():
        console.print("[red]❌ 笔记内容不能为空！[/red]")
        return []

    if question_types is None:
        question_types = SUPPORTED_TYPES
    question_types = [t for t in question_types if t in SUPPORTED_TYPES]
    if not question_types:
        console.print("[red]❌ 无有效题型！支持的题型：[/red]", SUPPORTED_TYPES)
        return []

    output_example = json.dumps(
        [
            {
                "content": "在 Python 中，关于字典键和字典值的特性，下面的说法哪一项是错误的？（注意：不要拆成两道题）",
                "type": "single_choice",
                "options": {
                    "A": "字典的键必须是可哈希（不可变）对象",
                    "B": "同一个字典中，键必须唯一",
                    "C": "字典的值可以是任意数据类型",
                    "D": "字典的值必须唯一，不能重复",
                },
                "answer": "D",
            }
        ],
        ensure_ascii=False,
    )

    prompt_template = PromptTemplate(
        template="""
        你是一位专业的教育出题专家，请严格按照以下要求生成考题：
        1. 基于笔记内容：{note_content}
        2. 生成 {question_num} 道题，题型包含：{question_types}
        3. 不同题型的字段要求：
           - 单选题（single_choice）：必须包含 content（题目内容）、type、options（选项，字典格式）、answer（正确选项字母，如"A"）
           - 简答题（short_answer）：包含 content、type、answer（正确答案文本）
           - 填空题（fill_blank）：包含 content、type、answer（正确答案文本）
        4. 输出格式必须是标准 JSON 数组，不允许任何额外文字、解释或格式错误，参考示例：
        {output_example}
        5. 单选题必须生成 {option_num} 个选项（1个正确，其余错误），选项字母为A/B/C/D...
        6. 题目难度适中，贴合笔记核心知识点，避免偏题怪题。
        7. 【重要】不要把同一个知识点拆成多道题：
           - 对于“Python 字典的键/值特性”这类相关点，只生成一道题，可以在同一道题中综合考察，不要出两道几乎一样的题目。
           - 同一批题目中，避免出现题干只差几个字但考察内容几乎相同的重复题。
        """,
        input_variables=[
            "note_content",
            "question_num",
            "question_types",
            "option_num",
            "output_example",
        ],
    )

    prompt = prompt_template.format(
        note_content=note_content,
        question_num=question_num,
        question_types=", ".join(question_types),
        option_num=SINGLE_CHOICE_OPTION_NUM,
        output_example=output_example,
    )

    try:
        console.print("[blue]🤖 正在生成考题...[/blue]")
        response = llm.invoke(prompt)
        questions = json.loads(response.content.strip())

        if not isinstance(questions, list):
            raise ValueError("返回结果不是数组格式")

        for q in questions:
            if not all(k in q for k in ["content", "type", "answer"]):
                raise ValueError(f"题目缺少关键字段：{q}")
            if q["type"] == "single_choice" and "options" not in q:
                raise ValueError(f"单选题缺少 options 字段：{q}")

        # 在单次生成结果内部做一次简单去重，避免“几乎一样”的题成对出现
        questions = _dedupe_questions_basic(questions)
        return questions
    except json.JSONDecodeError:
        console.print("[red]❌ LLM 返回非标准 JSON 格式：[/red]", response.content)
        return []
    except Exception as e:
        console.print("[red]❌ 生成考题失败：[/red]", str(e))
        return []


def _check_questions(questions):
    if not isinstance(questions, list):
        return False
    for q in questions:
        if not all(k in q for k in ["content", "type", "answer"]):
            return False
        if q["type"] == "single_choice" and "options" not in q:
            return False
    return True


def generate_questions_with_format_check(note_content, num=5, question_types=None):
    questions = generate_questions(note_content, num, question_types)
    if not _check_questions(questions):
        console.print("[yellow]⚠️  格式校验失败，尝试重新生成...[/yellow]")
        for _ in range(2):
            questions = generate_questions(note_content, num, question_types)
            if _check_questions(questions):
                return questions
        raise Exception("生成考题格式失败超过最大重试次数")
    return questions


__all__ = [
    "generate_questions",
    "generate_questions_with_format_check",
]

