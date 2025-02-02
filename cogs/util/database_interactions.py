import contextlib
import os
from typing import AsyncGenerator, Union

import asqlite as sql

DBQuizSettings = tuple[int, int, int, int, int, Union[int, None], int]
DBQuizQuestion = tuple[int, str, str, str, Union[str, None], int, int, int]
DBQuizChoice = tuple[int, int, str, bool]
DBUserStats = tuple[bool, int, str]
DBQuizAggregateStats = tuple[int, float, int, float, int, int, int]

_connection = None


async def get_persistent_connection() -> sql.Connection:
    """Get or create a persistent SQLite connection."""
    global _connection

    if _connection is None:
        _connection = await sql.connect(os.getenv("SQLITE_DATABASE"))

    return _connection


@contextlib.asynccontextmanager
async def get_db_context() -> AsyncGenerator[sql.Cursor, None]:
    """Context manager that provides a database connection and cursor."""

    conn: sql.Connection = await get_persistent_connection()
    async with conn.cursor() as cursor:
        yield cursor


async def create_tables_if_not_exist() -> None:
    """Init SQL statements to create required tables if they do not exist."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS managers (
                id INTEGER PRIMARY KEY,
                discord_id INTEGER UNIQUE NOT NULL,
                added_at INTEGER NOT NULL DEFAULT (unixepoch('now')),
                added_by INTEGER NOT NULL
            );
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL
            );
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_question_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                correct_answer_text TEXT NOT NULL,
                incorrect_answer_text TEXT NOT NULL,
                image TEXT,
                quiz_type INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                created_at INTEGER NOT NULL DEFAULT (unixepoch('now')),
                FOREIGN KEY(quiz_type) REFERENCES quiz_types(id)
            );
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_choice_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                choice_text TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                FOREIGN KEY(question_id) REFERENCES quiz_question_bank(id)
            );
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_settings (
                id INTEGER PRIMARY KEY,
                quiz_type INTEGER UNIQUE NOT NULL,
                length INTEGER NOT NULL,
                min_correct INTEGER NOT NULL,
                required_role INTEGER NOT NULL,
                passing_role INTEGER NOT NULL,
                passing_role_two INTEGER,
                non_passing_role INTEGER NOT NULL,
                quiz_passed_text TEXT,
                quiz_not_passed_text TEXT,
                FOREIGN KEY (quiz_type) REFERENCES quiz_types(id)
            );
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_stats (
                id INTEGER PRIMARY KEY,
                discord_id INTEGER NOT NULL,
                quiz_type INTEGER NOT NULL,
                passed BOOLEAN NOT NULL,
                timestamp INTEGER NOT NULL DEFAULT (unixepoch('now')),
                eth_wallet_address TEXT NOT NULL
            );
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS question_stats (
                id INTEGER PRIMARY KEY,
                discord_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                correct BOOLEAN NOT NULL,
                timestamp INTEGER NOT NULL DEFAULT (unixepoch('now'))
            );
            """
        )


async def check_if_manager_exists(user_id: int) -> bool:
    """Query database to check if `user_id` is present in the `managers` table.

    Returns `bool` whether or not the `user_id` was found.
    """
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT COUNT(managers.discord_id)
            FROM managers
            WHERE managers.discord_id = ?;
            """,
            (user_id,),
        )

        result = await cursor.fetchone()
        return result[0] >= 1


async def add_new_manager(manager_id: int, caller_id: int) -> None:
    """Insert a new manager into the `managers` table using their Discord ID."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            INSERT INTO managers (discord_id, added_by)
            VALUES (?, ?);
            """,
            (manager_id, caller_id),
        )


async def remove_current_manager(manager_id: int) -> bool:
    """Delete an existing manager from the `managers` table using their Discord ID.

    Returns `bool` if the deletion was successful or not.
    """
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            DELETE FROM managers
            WHERE managers.discord_id = ?
            RETURNING *;
            """,
            (manager_id,),
        )

        result = await cursor.fetchall()
        return len(result) >= 1


async def select_all_managers() -> list[tuple[int, int, int, int]]:
    """Select all existing bot managers from the `managers` table."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT *
            FROM managers;
            """
        )

        result = await cursor.fetchall()
        return result


async def select_all_quiz_types() -> list[tuple[int, str]]:
    """Select all existing quiz `id`s and `slug`s from the `quiz_types` table."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT *
            FROM quiz_types;
            """
        )

        result = await cursor.fetchall()
        return result


async def check_if_quiz_type_exists(slug: str) -> bool:
    """Query database to check if `quiz_type` is present in the `quiz_types` table."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT COUNT(quiz_types.slug)
            FROM quiz_types
            WHERE quiz_types.slug = ?;
            """,
            (slug,),
        )

        result = await cursor.fetchone()
        return result[0] >= 1


async def select_quiz_slug_to_quiz_id(slug: str) -> int:
    """Convert a quiz slug to quiz id."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT id
            FROM quiz_types
            WHERE quiz_types.slug = ?;
            """,
            (slug,),
        )

        result = await cursor.fetchone()
        return result[0]


async def add_quiz_type(slug: str) -> int:
    """Insert a new quiz type to the `quiz_types` table using a `type` string.

    Returns `id` associated with newly inserted slug.
    """
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            INSERT INTO quiz_types (slug)
            VALUES (?)
            RETURNING id;
            """,
            (slug,),
        )

        result = await cursor.fetchone()
        return result[0]


async def remove_quiz_type(slug: str) -> bool:
    """Delete an existing quiz type from the `quiz_types` table using a `slug` string.

    Returns `bool` whether the deletion was successful or not.
    """
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            DELETE FROM quiz_types
            WHERE quiz_types.slug = ?
            RETURNING *;
            """,
            (slug,),
        )

        result = await cursor.fetchall()
        return len(result) >= 1


async def select_quiz_settings(slug: str) -> DBQuizSettings:
    """Query database select the quiz settings of a specific quiz."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT qt.id, qs.length, qs.min_correct, qs.required_role, qs.passing_role, qs.passing_role_two, qs.non_passing_role
            FROM quiz_settings AS qs
            LEFT JOIN quiz_types AS qt ON qs.quiz_type = qt.id
            WHERE qt.slug = ?;
            """,
            (slug,),
        )

        result = await cursor.fetchone()
        return result


async def add_quiz_settings(
    quiz_id: int,
    quiz_length: int,
    quiz_min_correct: int,
    required_role: int,
    passing_role: int,
    passing_role_two: int,
    non_passing_role: int,
    quiz_passed_text: Union[str, None],
    quiz_not_passed_text: Union[str, None],
) -> None:
    """Insert quiz settings for a new quiz type."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            INSERT INTO quiz_settings (quiz_type, length, min_correct, required_role, passing_role, passing_role_two, non_passing_role, quiz_passed_text, quiz_not_passed_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                quiz_id,
                quiz_length,
                quiz_min_correct,
                required_role,
                passing_role,
                passing_role_two,
                non_passing_role,
                quiz_passed_text,
                quiz_not_passed_text,
            ),
        )


async def remove_quiz_settings(quiz_id: int) -> bool:
    """Delete a quiz's settings for a quiz that is being removed.

    Returns `bool` whether the deletion was successful or not.
    """
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            DELETE FROM quiz_settings
            WHERE quiz_settings.id = ?
            RETURNING *;
            """,
            (quiz_id,),
        )

        result = await cursor.fetchall()
        return len(result) >= 1


async def edit_quiz_settings_length(quiz_length: int, quiz_id: int) -> None:
    """Update a quiz's length setting."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            UPDATE quiz_settings
            SET length = ?
            WHERE quiz_type = ?;
            """,
            (quiz_length, quiz_id),
        )


async def edit_quiz_settings_min_correct(quiz_min_correct: int, quiz_id: int) -> None:
    """Update a quiz's minimum correct setting."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            UPDATE quiz_settings
            SET min_correct = ?
            WHERE quiz_type = ?;
            """,
            (quiz_min_correct, quiz_id),
        )


async def add_quiz_question(
    question_text: str,
    correct_answer_text: str,
    incorrect_answer_text: str,
    image: str,
    quiz_id: int,
    created_by: int,
) -> int:
    """Insert a new quiz question.

    Retruns the `id` of the new question.
    """
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            INSERT INTO quiz_question_bank (question_text, correct_answer_text, incorrect_answer_text, image, quiz_type, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id;
            """,
            (
                question_text,
                correct_answer_text,
                incorrect_answer_text,
                image,
                quiz_id,
                created_by,
            ),
        )

        result = await cursor.fetchone()
        return result[0]


async def add_quiz_question_choice(
    question_id: int, choice_text: str, is_correct: bool
) -> None:
    """Insert a new quiz question choice."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            INSERT INTO quiz_choice_bank (question_id, choice_text, is_correct)
            VALUES (?, ?, ?);
            """,
            (question_id, choice_text, is_correct),
        )


async def remove_quiz_question(question_id: int) -> bool:
    """Delete a quiz's settings.

    Returns `bool` whether the deletion was successful or not.
    """
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            DELETE FROM quiz_question_bank
            WHERE id = ?
            RETURNING *;
            """,
            (question_id,),
        )

        result = await cursor.fetchall()
        return len(result) >= 1


async def remove_quiz_question_choice(question_id: int) -> bool:
    """Delete all quiz choices associated with a question `id`

    Returns `bool` whether the deletion was successful or not.
    """
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            DELETE FROM quiz_choice_bank
            WHERE question_id = ?
            RETURNING *;
            """,
            (question_id,),
        )

        result = await cursor.fetchall()
        return len(result) >= 1


async def list_quiz_questions(quiz_id: int) -> list[DBQuizQuestion]:
    """Select all quiz questions for a specific `quiz_id`."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT *
            FROM quiz_question_bank
            WHERE quiz_type = ?;
            """,
            (quiz_id,),
        )

        result = await cursor.fetchall()
        return result


async def list_quiz_question_choices(question_id: int) -> list[DBQuizChoice]:
    """Select all quiz question choices for a specific `question_id`."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT *
            FROM quiz_choice_bank
            WHERE question_id = ?;
            """,
            (question_id,),
        )

        result = await cursor.fetchall()
        return result


async def check_quiz_question_exists(question_id: int) -> bool:
    """Query database to check if a question `id` exists."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT COUNT(id)
            FROM quiz_question_bank
            WHERE id = ?;
            """,
            (question_id,),
        )

        result = await cursor.fetchone()
        return result[0] >= 1


async def insert_quiz_stat(
    discord_id: int, quiz_type: int, passed: bool, eth_wallet_address: str
) -> None:
    """Insert a new quiz stat."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            INSERT INTO quiz_stats (discord_id, quiz_type, passed, eth_wallet_address)
            VALUES (?, ?, ?, ?);
            """,
            (discord_id, quiz_type, passed, eth_wallet_address),
        )


async def insert_question_stat(
    discord_id: int, question_id: int, correct: bool
) -> None:
    """Insert a new question stat."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            INSERT INTO question_stats (discord_id, question_id, correct)
            VALUES (?, ?, ?);
            """,
            (discord_id, question_id, correct),
        )


async def select_quiz_stats_for_user(discord_id: int) -> list[DBUserStats]:
    """Select stats for quizzes that a user passed/failed.

    Returns `bool` passed, `int` timestamp, `str` eth wallet address, and quiz slug.
    """
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT
                qs.passed,
                qs.timestamp,
                qs.eth_wallet_address,
                qt.slug
            FROM
                quiz_stats AS qs
            JOIN
                quiz_types AS qt
            ON
                qs.quiz_type = qt.id
            WHERE
                qs.discord_id = ?
            ORDER BY
                qs.timestamp DESC;
            """,
            (discord_id),
        )

        result = await cursor.fetchall()
        return result


async def select_quiz_stats_aggregate(
    quiz_id: int,
) -> DBQuizAggregateStats:
    """Select BOTH global aggregate stats of ALL quizzes AND aggregate stats of a specific quiz."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            WITH
                total_stats AS (
                    SELECT
                        COUNT(*) AS total_rows,
                        CAST(SUM(CASE WHEN passed THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS total_pass_ratio
                    FROM
                        quiz_stats
                ),
                per_quiz_type_ratio AS (
                    SELECT
                        quiz_type,
                        COUNT(*) AS total_attempts,
                        CAST(SUM(CASE WHEN passed THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS pass_ratio,
                        MIN(timestamp) AS oldest_timestamp,
                        MAX(timestamp) AS newest_timestamp
                    FROM
                        quiz_stats
                    GROUP BY
                        quiz_type
                )
            SELECT
                ts.total_rows,
                ts.total_pass_ratio,
                pq.quiz_type,
                pq.pass_ratio,
                pq.total_attempts,
                pq.oldest_timestamp,
                pq.newest_timestamp
            FROM
                total_stats ts
            LEFT JOIN
                per_quiz_type_ratio pq ON 1 = 1
            WHERE
                pq.quiz_type = ?
            ORDER BY
                pq.quiz_type;
            """,
            (quiz_id,),
        )

        result = await cursor.fetchone()
        return result
