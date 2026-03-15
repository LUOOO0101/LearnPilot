"""Database access helpers for Examor CLI."""

import json
import time

import pymysql
from rich.console import Console

from examor_cli.config import DATABASE_CONFIG

console = Console()


def get_db_connection():
    """获取数据库连接（不变）"""
    max_retries = 5
    retry_count = 0
    while retry_count < max_retries:
        try:
            conn = pymysql.connect(
                host=DATABASE_CONFIG["host"],
                port=DATABASE_CONFIG["port"],
                user=DATABASE_CONFIG["user"],
                password=DATABASE_CONFIG["password"],
                database=DATABASE_CONFIG["database"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            return conn
        except pymysql.MySQLError as e:
            retry_count += 1
            console.print(f"[red]数据库连接失败（{retry_count}/{max_retries}）：{e}[/red]")
            time.sleep(2)
    raise Exception("数据库连接超时！请检查数据库容器是否运行。")


def init_database():
    """初始化数据库表（新增 options 字段）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 题目表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    content TEXT NOT NULL COMMENT '题目内容',
                    type VARCHAR(50) NOT NULL COMMENT '题型',
                    options TEXT NULL COMMENT '单选题选项（JSON格式）',
                    answer TEXT NOT NULL COMMENT '正确答案',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

            # 答题记录表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS answer_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    question_id INT COMMENT '关联考题ID',
                    user_answer TEXT NOT NULL COMMENT '用户答案',
                    score INT COMMENT '分数（0-100）',
                    feedback TEXT COMMENT '批改反馈',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '答题时间',
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

            # 用户表（简单单用户默认支持，后续可扩展）
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(50) NOT NULL DEFAULT 'default',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

            # 用户-题目统计表（长期记忆：正确率 / 次数）
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_question_stats (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    question_id INT NOT NULL,
                    total_attempts INT NOT NULL DEFAULT 0,
                    correct_attempts INT NOT NULL DEFAULT 0,
                    last_score INT DEFAULT NULL,
                    last_answer_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_user_question (user_id, question_id),
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

            # 确保存在一个默认用户（id=1）
            cursor.execute(
                """
                INSERT INTO users (id, name)
                VALUES (1, 'default')
                ON DUPLICATE KEY UPDATE name = VALUES(name);
                """
            )
        conn.commit()
        console.print("[green]✅ 数据库表初始化成功！[/green]")
    except pymysql.MySQLError as e:
        console.print(f"[red]❌ 数据库表初始化失败：{e}[/red]")
    finally:
        conn.close()


def save_question_to_db(question_list):
    """批量保存考题（新增 options 字段）"""
    if not question_list:
        console.print("[yellow]⚠️  无考题可保存[/yellow]")
        return

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO questions (content, type, options, answer)
            VALUES (%s, %s, %s, %s)
            """
            data = []
            for q in question_list:
                options = (
                    json.dumps(q.get("options", {}), ensure_ascii=False)
                    if q["type"] == "single_choice"
                    else None
                )
                data.append((q["content"], q["type"], options, q["answer"]))

            cursor.executemany(sql, data)
        conn.commit()
        console.print(f"[green]✅ 成功保存 {cursor.rowcount} 道题到数据库！[/green]")
    except pymysql.MySQLError as e:
        console.print(f"[red]❌ 保存考题失败：{e}[/red]")
    finally:
        conn.close()


def save_answer_result(question_id, user_answer, score, feedback):
    """保存答题结果（不变）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO answer_records (question_id, user_answer, score, feedback)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (question_id, user_answer, score, feedback))
        conn.commit()
        console.print("[green]✅ 答题结果已保存到数据库！[/green]")
        # 顺带更新长期记忆统计（默认用户 id=1）
        _update_user_question_stats(user_id=1, question_id=question_id, score=score)
    except pymysql.MySQLError as e:
        console.print(f"[red]❌ 保存答题结果失败：{e}[/red]")
    finally:
        conn.close()


def clear_all_data():
    """清空所有考题、答题记录与用户题目统计（危险操作）。

    顺序：先清空 answer_records，再清空 user_question_stats，最后清空 questions。
    清空后重置各表自增 ID，新题目将从 id=1 开始。
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM answer_records")
            cursor.execute("DELETE FROM user_question_stats")
            cursor.execute("DELETE FROM questions")
            # 重置自增 ID，使新题目从 1 开始
            cursor.execute("ALTER TABLE answer_records AUTO_INCREMENT = 1")
            cursor.execute("ALTER TABLE user_question_stats AUTO_INCREMENT = 1")
            cursor.execute("ALTER TABLE questions AUTO_INCREMENT = 1")
        conn.commit()
        console.print(
            "[green]✅ 已清空所有考题、答题记录和用户题目统计，新题目 ID 将从 1 开始[/green]"
        )
    except pymysql.MySQLError as e:
        console.print(f"[red]❌ 清空数据失败：{e}[/red]")
    finally:
        conn.close()

def get_all_questions():
    """查询所有考题（解析 options 字段）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM questions ORDER BY created_at DESC")
            questions = cursor.fetchall()

        for q in questions:
            options_str = q.get("options", "")
            if q["type"] == "single_choice" and options_str:
                try:
                    q["options"] = json.loads(options_str)
                except json.JSONDecodeError:
                    q["options"] = {}
            else:
                q["options"] = {}

        return questions
    except pymysql.MySQLError as e:
        console.print(f"[red]❌ 查询考题失败：{e}[/red]")
        return []
    finally:
        conn.close()


def _update_user_question_stats(user_id: int, question_id: int, score: int) -> None:
    """更新用户在某题上的统计数据（总次数 / 正确次数 / 最近分数）。"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, total_attempts, correct_attempts
                FROM user_question_stats
                WHERE user_id = %s AND question_id = %s
                """,
                (user_id, question_id),
            )
            row = cursor.fetchone()

            correct_inc = 1 if score is not None and score >= 60 else 0

            if row:
                cursor.execute(
                    """
                    UPDATE user_question_stats
                    SET total_attempts = total_attempts + 1,
                        correct_attempts = correct_attempts + %s,
                        last_score = %s,
                        last_answer_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (correct_inc, score, row["id"]),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO user_question_stats
                        (user_id, question_id, total_attempts, correct_attempts, last_score)
                    VALUES (%s, %s, 1, %s, %s)
                    """,
                    (user_id, question_id, correct_inc, score),
                )
        conn.commit()
    except pymysql.MySQLError as e:
        console.print(f"[red]❌ 更新用户题目统计失败：{e}[/red]")
    finally:
        conn.close()

__all__ = [
    "get_db_connection",
    "init_database",
    "save_question_to_db",
    "save_answer_result",
    "get_all_questions",
    "clear_all_data",
]

