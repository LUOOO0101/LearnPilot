"""Core package for Examor CLI.

High-level API re-exports for convenient use:

    from examor_cli import generate_questions, evaluate_answer
"""

from .core import (
    generate_questions,
    generate_questions_with_format_check,
    evaluate_answer,
)
from .db import (
    get_db_connection,
    init_database,
    save_question_to_db,
    save_answer_result,
    get_all_questions,
)

__all__ = [
    "generate_questions",
    "generate_questions_with_format_check",
    "evaluate_answer",
    "get_db_connection",
    "init_database",
    "save_question_to_db",
    "save_answer_result",
    "get_all_questions",
]

