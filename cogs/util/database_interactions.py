import contextlib
import os
import asqlite as sql
from typing import AsyncGenerator

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
                id INTEGER PRIMARY KEY,
                class_type TEXT UNIQUE NOT NULL
            );
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_question_bank (
                id INTEGER PRIMARY KEY,
                question_text TEXT NOT NULL,
                quiz_type INTEGER NOT NULL,
                created_by INTEGER UNIQUE NOT NULL,
                created_at INTEGER NOT NULL DEFAULT (unixepoch('now')),
                FOREIGN KEY(quiz_type) REFERENCES quiz_types(id)
            );
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_choice_bank (
                id INTEGER PRIMARY KEY,
                question_id INTEGER NOT NULL,
                choice_text NOT NULL,
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
                FOREIGN KEY (quiz_type) REFERENCES quiz_types(id)
            );
            """
        )


async def check_if_manager_exists(user_id: int) -> bool:
    """Query database to check if `user_id` is present in the `managers` table."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT COUNT(managers.discord_id)
            FROM managers
            WHERE managers.discord_id = ?;
            """,
            (user_id,),
        )

        return await cursor.fetchone()[0] >= 1


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
    """Delete an existing manager from the `managers` table using their Discord ID."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            DELETE FROM managers
            WHERE managers.discord_id = ?
            RETURNING *;
            """,
            (manager_id,),
        )

        return len(await cursor.fetchall()) >= 1


async def select_all_managers() -> list[tuple[int, int, int, int]]:
    """Select all existing bot managers from the `managers` table."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT *
            FROM managers;
            """
        )

        return await cursor.fetchall()


async def select_all_quiz_types() -> list[tuple[int, str]]:
    """Select all existing quiz types from the `quiz_types` table."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT *
            FROM quiz_types;
            """
        )

        return await cursor.fetchall()


async def check_if_quiz_type_exists(quiz_type: str) -> bool:
    """Query database to check if `quiz_type` is present in the `quiz_types` table."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT COUNT(quiz_types.class_type)
            FROM quiz_types
            WHERE quiz_types.class_type = ?;
            """,
            (quiz_type,),
        )

        return await cursor.fetchone()[0] >= 1


async def select_quiz_str_to_quiz_id(quiz_type: str) -> int:
    """Convert a quiz str to quiz id."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT id
            FROM quiz_types
            WHERE quiz_types.class_type = ?;
            """,
            (quiz_type,),
        )

        return await cursor.fetchone()[0]


async def add_quiz_type(quiz_type: str) -> int:
    """Insert a new quiz type to the `quiz_types` table using a `type` string."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            INSERT INTO quiz_types (class_type)
            VALUES (?)
            RETURNING id;
            """,
            (quiz_type,),
        )

        return await cursor.fetchone()[0]


async def remove_quiz_type(quiz_type: str) -> bool:
    """Delete an existing quiz type from the `quiz_types` table using a `type` string."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            DELETE FROM quiz_types
            WHERE quiz_types.class_type = ?
            RETURNING *;
            """,
            (quiz_type,),
        )

        return len(await cursor.fetchall()) >= 1


async def select_quiz_settings(quiz_type: str) -> tuple[int, int, int]:
    """Query database select the quiz settings of a specific quiz."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            SELECT qs.id, qs.length, qs.min_correct
            FROM quiz_settings AS qs
            LEFT JOIN quiz_types AS qt ON qs.quiz_type = qt.id
            WHERE qt.class_type = ?;
            """,
            (quiz_type,),
        )

        return await cursor.fetchone()


async def add_quiz_settings(
    quiz_id: int, quiz_length: int, quiz_min_correct: int
) -> None:
    """Insert quiz settings for a new quiz type."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            INSERT INTO quiz_settings (quiz_type, length, min_correct)
            VALUES (?, ?, ?);
            """,
            (quiz_id, quiz_length, quiz_min_correct),
        )


async def remove_quiz_settings(quiz_id: int) -> bool:
    """Delete a quiz's settings for a quiz that is being removed."""
    async with get_db_context() as cursor:
        await cursor.execute(
            """
            DELETE FROM quiz_settings
            WHERE quiz_settings.id = ?
            RETURNING *;
            """,
            (quiz_id,),
        )

        return len(await cursor.fetchall()) >= 1


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
