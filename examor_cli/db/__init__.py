"""Database access subpackage for Examor CLI."""

from .repo import (
    get_db_connection,
    init_database,
    save_question_to_db,
    save_answer_result,
    get_all_questions,
    clear_all_data,
)

__all__ = [
    "get_db_connection",
    "init_database",
    "save_question_to_db",
    "save_answer_result",
    "get_all_questions",
    "clear_all_data",
]

