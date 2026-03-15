"""CLI entrypoint for Examor CLI."""

import json

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from examor_cli.config import TYPE_CN_MAP, DEFAULT_QUESTION_NUM
from examor_cli.db import (
    init_database,
    save_question_to_db,
    save_answer_result,
    get_all_questions,
    clear_all_data,
)
from examor_cli.memory import (
    session_memory,
    get_user_profile,
    DEFAULT_USER_ID,
)
from examor_cli.core import generate_questions, evaluate_answer
from examor_cli.rag import PDFRAG
from examor_cli.agent import PDFExamAgent, run_learning_agent

console = Console()


@click.group()
@click.version_option(version="1.0.0", help="显示版本号")
def cli():
    """
    📚 Examor-CLI - 基于AI的智能出题/批改系统
    核心功能：生成考题、答题批改、查询历史考题
    """


@cli.command(name="init-db")
def init_db():
    """初始化数据库表（首次运行必执行）"""
    console.print("[blue]🔧 正在初始化数据库...[/blue]")
    init_database()


@cli.command(name="clear-db")
def clear_db():
    """清空所有考题、答题记录和用户题目统计（危险操作）"""
    console.print(
        "[red]⚠️  即将清空 questions、answer_records、user_question_stats 表中的所有数据，"
        "用户画像与错题本将一并清除，新题目 ID 将从 1 开始。此操作不可恢复！[/red]"
    )
    if not Confirm.ask("确定要继续吗？"):
        console.print("[yellow]已取消清空操作。[/yellow]")
        return

    clear_all_data()


@cli.command(name="generate")
@click.option("--note", prompt="📝 请输入笔记内容", help="用于生成考题的笔记文本")
@click.option(
    "--num",
    default=DEFAULT_QUESTION_NUM,
    help=f"生成题目数量（默认{DEFAULT_QUESTION_NUM}）",
)
@click.option(
    "--types",
    default="single_choice,short_answer",
    help="题型（逗号分隔，如 single_choice,fill_blank）",
)
def generate(note, num, types):
    """生成考题并保存到数据库"""
    question_types = [t.strip() for t in types.split(",")]
    # 更新短期记忆中的题型偏好
    session_memory.update_preferences(preferred_types=question_types)

    # 读取长期记忆画像，根据历史弱项题型/易错题做轻微偏向
    profile = get_user_profile(DEFAULT_USER_ID)
    weak_types = profile.get("weak_types", [])
    hard_questions = profile.get("hard_questions", [])

    enhanced_note = note
    if weak_types:
        enhanced_note += (
            "\n\n【出题偏好提醒】请适当多出一些以下题型，帮助用户练习易错题型："
            + ", ".join(weak_types)
            + "。"
        )

    # 仅取少量易错题，避免 prompt 过长
    if hard_questions:
        top_hard = hard_questions[:5]
        enhanced_note += "\n\n【历史易错题提示】用户在以下题目上错误较多，请在出新题时优先覆盖这些题考察的知识点（不要直接重复原题）：\n"
        for h in top_hard:
            content = h["content"]
            short = content[:40] + "..." if len(content) > 40 else content
            acc = int(h["accuracy"] * 100) if h["accuracy"] is not None else 0
            enhanced_note += f"- 题ID {h['question_id']}，题型 {h['type']}，历史正确率约 {acc}%：{short}\n"

    questions = generate_questions(enhanced_note, num, question_types)
    if not questions:
        console.print("[red]❌ 未生成任何考题！[/red]")
        return

    console.print("\n[green]🎯 生成的考题如下：[/green]")
    for i, q in enumerate(questions, 1):
        console.print(f"\n{i}. [bold]{TYPE_CN_MAP.get(q['type'], q['type'])}[/bold]")
        console.print(f"   题目：{q['content']}")
        if q["type"] == "single_choice" and "options" in q:
            console.print("   选项：")
            for opt_key, opt_value in q["options"].items():
                console.print(f"      {opt_key}. {opt_value}")
        console.print(f"   正确答案：{q['answer']}")

    if Confirm.ask("\n📥 是否保存到数据库？"):
        save_question_to_db(questions)


@cli.command(name="answer")
@click.option(
    "--question-id",
    type=int,
    prompt="🔢 请输入考题ID（可通过 list 命令查看）",
    help="考题ID",
)
def answer(question_id):
    """根据考题ID答题并获取AI批改"""
    questions = get_all_questions()
    target_question = next((q for q in questions if q["id"] == question_id), None)
    if not target_question:
        console.print("[red]❌ 未找到该考题！[/red]")
        return

    console.print("\n[blue]📖 题目信息：[/blue]")
    console.print(
        f"题型：{TYPE_CN_MAP.get(target_question['type'], target_question['type'])}"
    )
    console.print(f"题目：{target_question['content']}")
    if target_question["type"] == "single_choice" and target_question["options"]:
        console.print("选项：")
        for opt_key, opt_value in target_question["options"].items():
            console.print(f"  {opt_key}. {opt_value}")

    user_answer = Prompt.ask("\n✍️  请输入你的答案")

    score, feedback = evaluate_answer(
        question_content=target_question["content"],
        user_answer=user_answer,
        correct_answer=target_question["answer"],
    )

    console.print("\n[green]🎯 批改结果：[/green]")
    console.print(f"分数：[bold]{score}[/bold]/100")
    console.print(f"反馈：{feedback}")

    if Confirm.ask("\n📥 是否保存答题结果到数据库？"):
        save_answer_result(
            question_id=target_question["id"],
            user_answer=user_answer,
            score=score,
            feedback=feedback,
        )


@cli.command(name="batch-answer")
@click.option(
    "--ids",
    prompt="🔢 请输入要答题的考题ID（逗号分隔，如 1,2,3）",
    help="批量答题的ID列表",
)
def batch_answer(ids):
    """批量答题（支持多道题连续作答，仅批改后显示答案）"""
    try:
        question_ids = [int(id.strip()) for id in ids.split(",")]
    except ValueError:
        console.print("[red]❌ ID格式错误！请输入数字，逗号分隔[/red]")
        return

    all_questions = get_all_questions()
    target_questions = []
    for q_id in question_ids:
        q = next((item for item in all_questions if item["id"] == q_id), None)
        if q:
            target_questions.append(q)
        else:
            console.print(f"[yellow]⚠️  ID={q_id} 的考题不存在，已跳过[/yellow]")

    if not target_questions:
        console.print("[red]❌ 无有效考题ID！[/red]")
        return

    console.print(f"\n[blue]🚀 开始批量答题，共 {len(target_questions)} 道题[/blue]")
    answer_results = []

    for i, q in enumerate(target_questions, 1):
        console.print(f"\n==================== 第 {i} 道题 ====================")
        console.print(f"题型：{TYPE_CN_MAP.get(q['type'], q['type'])}")
        console.print(f"题目：{q['content']}")
        if q["type"] == "single_choice" and q["options"]:
            console.print("选项：")
            for opt_key, opt_value in q["options"].items():
                console.print(f"  {opt_key}. {opt_value}")

        user_answer = Prompt.ask("\n✍️  请输入你的答案", default="")
        if not user_answer:
            console.print("[yellow]⚠️  未输入答案，跳过该题[/yellow]")
            continue

        score, feedback = evaluate_answer(
            question_content=q["content"],
            user_answer=user_answer,
            correct_answer=q["answer"],
        )

        console.print("\n[green]🎯 批改结果：[/green]")
        console.print(f"分数：[bold]{score}[/bold]/100")
        console.print(f"正确答案：[bold]{q['answer']}[/bold]")
        console.print(f"反馈：{feedback}")

        answer_results.append(
            {
                "question_id": q["id"],
                "user_answer": user_answer,
                "score": score,
                "feedback": feedback,
            }
        )

    if answer_results and Confirm.ask("\n📥 是否保存所有答题结果到数据库？"):
        for res in answer_results:
            save_answer_result(
                question_id=res["question_id"],
                user_answer=res["user_answer"],
                score=res["score"],
                feedback=res["feedback"],
            )
        console.print("[green]✅ 批量答题结果已保存！[/green]")

    console.print("\n[green]🎉 批量答题完成！[/green]")
    total_score = sum([res["score"] for res in answer_results])
    avg_score = total_score / len(answer_results) if answer_results else 0
    console.print(f"总分：{total_score} | 平均分：{avg_score:.1f}")


@cli.command(name="list")
def list_questions():
    """查询所有已生成的考题（显示选项摘要）"""
    console.print("[blue]📜 正在查询历史考题...[/blue]")
    questions = get_all_questions()
    if not questions:
        console.print("[yellow]⚠️  暂无历史考题[/yellow]")
        return

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("ID", width=6)
    table.add_column("题型", width=10)
    table.add_column("题目内容", width=40)
    table.add_column("选项摘要", width=20)
    table.add_column("创建时间", width=20)

    for q in questions:
        if q["type"] == "single_choice" and q["options"]:
            opt_summary = "|".join(
                [f"{k}:{v[:10]}..." for k, v in q["options"].items()]
            )
        else:
            opt_summary = "-"

        content = q["content"][:38] + "..." if len(q["content"]) > 40 else q["content"]

        table.add_row(
            str(q["id"]),
            TYPE_CN_MAP.get(q["type"], q["type"]),
            content,
            opt_summary,
            q["created_at"].strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@cli.command(name="list-questions")
@click.option("--page", default=1, help="页码（默认第1页）")
@click.option("--page-size", default=10, help="每页显示题目数量（默认10）")
@click.option("--type", "type_", default="", help="按题型筛选（如 single_choice）")
@click.option("--keyword", default="", help="按题目关键词筛选")
def list_questions_paged(page, page_size, type_, keyword):
    """分页/筛选查询题目（隐藏答案/选项，仅展示基础信息）"""
    console.print("[blue]📜 正在查询考题列表（仅展示基础信息）...[/blue]")
    questions = get_all_questions()

    if type_:
        questions = [q for q in questions if q["type"] == type_.strip()]
    if keyword:
        questions = [q for q in questions if keyword.strip() in q["content"]]

    if not questions:
        console.print("[yellow]⚠️  暂无符合条件的考题[/yellow]")
        return

    total = len(questions)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_questions = questions[start:end]

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("ID", width=6)
    table.add_column("题型", width=10)
    table.add_column("题目内容", width=50)
    table.add_column("创建时间", width=20)

    for q in paginated_questions:
        content = (
            q["content"][:48] + "..." if len(q["content"]) > 50 else q["content"]
        )
        table.add_row(
            str(q["id"]),
            TYPE_CN_MAP.get(q["type"], q["type"]),
            content,
            q["created_at"].strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)
    console.print(
        f"\n[green]📊 共 {total} 道题 | 当前第 {page} 页 | 每页 {page_size} 道[/green]"
    )
    console.print(
        "[yellow]💡 提示：使用 answer 命令 + ID 答题，批改后才会显示正确答案[/yellow]"
    )


@cli.command(name="list-wrong")
def list_wrong():
    """查看易错题（错题本：作答≥3次且正确率<60%的题目）"""
    profile = get_user_profile(DEFAULT_USER_ID)
    hard_questions = profile.get("hard_questions", [])

    if not hard_questions:
        console.print("[green]当前没有符合条件的易错题，继续保持！[/green]")
        return

    table = Table(show_header=True, header_style="bold red")
    table.add_column("题ID", width=6)
    table.add_column("题型", width=10)
    table.add_column("作答次数", width=8)
    table.add_column("答对次数", width=8)
    table.add_column("正确率", width=8)
    table.add_column("题目内容", width=60)

    for h in hard_questions:
        content = h["content"]
        short = content[:58] + "..." if len(content) > 60 else content
        acc = h["accuracy"] or 0.0
        acc_str = f"{acc * 100:.0f}%"
        table.add_row(
            str(h["question_id"]),
            TYPE_CN_MAP.get(h["type"], h["type"]),
            str(h["total_attempts"]),
            str(h["correct_attempts"]),
            acc_str,
            short,
        )

    console.print(
        "[blue]📕 易错题本（按正确率从低到高排序，作答≥3次且正确率<60%）：[/blue]"
    )
    console.print(table)


@cli.command(name="build-vector-db")
@click.option("--file", prompt="PDF 文件路径", help="要上传的 PDF")
def build_vector_db(file):
    """构建 PDF 知识库向量库"""
    rag = PDFRAG()
    docs = rag.load_pdf(file)
    chunks = rag.split_text(docs)
    rag.build_vector_db(chunks)
    console.print("[green]✅ 向量库构建完成！[/green]")


@cli.command(name="rag-agent-generate-pdf")
@click.option(
    "--query",
    prompt="请输入要生成考题的知识点",
    help="如 Python 字典、列表操作等",
)
def rag_agent_generate_pdf(query):
    """基于 PDF 知识库 + Agent 生成考题"""
    agent = PDFExamAgent()
    questions = agent.generate_agent_questions(query)
    for i, q in enumerate(questions, 1):
        console.print(f"\n{i}. {q['type']}")
        console.print(f"题目：{q['content']}")
        if q["type"] == "single_choice":
            for k, v in q["options"].items():
                console.print(f"   {k}. {v}")
        console.print(f"正确答案：{q['answer']}")


@cli.command(name="rag-retrieve")
@click.option("--query", prompt="请输入检索内容")
def rag_retrieve(query):
    """测试 RAG 检索效果"""
    rag = PDFRAG()
    content = rag.retrieve(query)
    console.print("[green]检索结果：[/green]")
    console.print(content)


@cli.command(name="agent")
@click.option(
    "--query",
    prompt="请输入你的需求（例如：给我学习建议 / 根据 Python 字典知识点出题 / 看看我的错题本）",
    help="自然语言描述需求，Agent 会规划调用工具并回复",
)
def agent_cmd(query):
    """智能学习助手：根据需求规划调用工具（画像、错题本、RAG、出题、学习建议等）"""
    console.print("[blue]🤖 学习助手正在规划并执行...[/blue]")
    try:
        result = run_learning_agent(query.strip() or "请给我当前的学习建议。")
        console.print("[green]助手回复：[/green]")
        console.print(result)
    except Exception as e:
        console.print(f"[red]执行失败：{e}[/red]")


if __name__ == "__main__":
    cli()

