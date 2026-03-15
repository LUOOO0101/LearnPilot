"""Simple memory manager for Examor CLI.

Includes:
 - SessionMemory: 短期记忆（进程内）
 - get_user_profile: 从数据库读取长期表现（按题型统计）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from examor_cli.db import get_db_connection

DEFAULT_USER_ID = 1


@dataclass
class SessionMemory:
    """短期记忆：仅在本次进程内有效。"""

    user_id: int = DEFAULT_USER_ID
    preferences: Dict[str, Any] = field(
        default_factory=lambda: {
            "preferred_types": ["single_choice", "short_answer"],
            "preferred_difficulty": "中等",
        }
    )
    recent_wrong_points: set[str] = field(default_factory=set)

    def update_preferences(self, **kwargs: Any) -> None:
        self.preferences.update(kwargs)

    def remember_wrong_point(self, knowledge_point: str) -> None:
        if knowledge_point:
            self.recent_wrong_points.add(knowledge_point)


# 单进程 CLI 下，全局一个 session memory 即可
session_memory = SessionMemory()


def get_user_profile(user_id: int = DEFAULT_USER_ID) -> Dict[str, Any]:
    """从数据库统计用户历史表现，返回简要画像。

    返回内容包含：
      - type_perf: 按题型聚合后的表现（总次数 / 正确次数 / 正确率）
      - weak_types: 弱项题型列表
      - hard_questions: 易错题列表（按题目粒度）
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.question_id,
                    q.content,
                    q.type,
                    s.total_attempts,
                    s.correct_attempts
                FROM user_question_stats s
                JOIN questions q ON s.question_id = q.id
                WHERE s.user_id = %s
                """,
                (user_id,),
            )
            rows: List[Dict[str, Any]] = cursor.fetchall()
    finally:
        conn.close()

    type_perf: Dict[str, Dict[str, Any]] = {}
    weak_types: list[str] = []
    hard_questions: list[Dict[str, Any]] = []

    for r in rows:
        t = r["type"]
        total = r["total_attempts"] or 0
        correct = r["correct_attempts"] or 0
        if t not in type_perf:
            type_perf[t] = {"total": 0, "correct": 0}
        type_perf[t]["total"] += total
        type_perf[t]["correct"] += correct

        acc = correct / total if total > 0 else 0.0
        # 定义“易错题”：作答次数 >=3 且正确率 < 60%
        if total >= 3 and acc < 0.6:
            hard_questions.append(
                {
                    "question_id": r["question_id"],
                    "content": r["content"],
                    "type": t,
                    "total_attempts": total,
                    "correct_attempts": correct,
                    "accuracy": acc,
                }
            )

    for t, stats in type_perf.items():
        total = stats["total"]
        correct = stats["correct"]
        acc = correct / total if total > 0 else 0.0
        stats["accuracy"] = acc
        # 简单规则：正确率低于 60% 视为弱项题型
        if total >= 3 and acc < 0.6:
            weak_types.append(t)

    # 按正确率从低到高排序 hard_questions，便于前端展示和出题参考
    hard_questions.sort(key=lambda x: (x["accuracy"], -x["total_attempts"]))

    return {
        "weak_types": weak_types,
        "type_perf": type_perf,
        "hard_questions": hard_questions,
    }


__all__ = [
    "SessionMemory",
    "session_memory",
    "get_user_profile",
    "DEFAULT_USER_ID",
]

