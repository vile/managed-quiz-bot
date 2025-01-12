import contextlib
import os
import sqlite3 as sql
from typing import Generator, Tuple


@contextlib.contextmanager
def get_db_context() -> Generator[Tuple[sql.Connection, sql.Cursor], None, None]:
    """Context manager that provides a database connection and cursor."""
    with contextlib.closing(sql.connect(os.getenv("SQLITE_DATABASE"))) as conn:
        with conn:  # Automatically handles commit/rollback
            with contextlib.closing(conn.cursor()) as cursor:
                yield conn, cursor


def create_tables_if_not_exist() -> None:
    """Init SQL statements to create required tables if they do not exist."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS managers (
                id INTEGER PRIMARY KEY,
                discord_id INTEGER UNIQUE NOT NULL,
                added_at INTEGER NOT NULL DEFAULT (unixepoch('now')),
                added_by INTEGER NOT NULL
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_types (
                id INTEGER PRIMARY KEY,
                class_type TEXT UNIQUE NOT NULL
            );
            """
        )

        cursor.execute(
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

        cursor.execute(
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

        cursor.execute(
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


def check_if_manager_exists(user_id: int) -> bool:
    """Query database to check if `user_id` is present in the `managers` table."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            SELECT COUNT(managers.discord_id)
            FROM managers
            WHERE managers.discord_id = ?;
            """,
            (user_id,),
        )

        return cursor.fetchone()[0] >= 1


def add_new_manager(manager_id: int, caller_id: int) -> None:
    """Insert a new manager into the `managers` table using their Discord ID."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            INSERT INTO managers (discord_id, added_by)
            VALUES (?, ?);
            """,
            (manager_id, caller_id),
        )


def remove_current_manager(manager_id: int) -> bool:
    """Delete an existing manager from the `managers` table using their Discord ID."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            DELETE FROM managers
            WHERE managers.discord_id = ?
            RETURNING *;
            """,
            (manager_id,),
        )

        return len(cursor.fetchall()) >= 1


def select_all_managers() -> list[tuple[int, int, int, int]]:
    """Select all existing bot managers from the `managers` table."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            SELECT *
            FROM managers;
            """
        )

        return cursor.fetchall()


def select_all_quiz_types() -> list[tuple[int, str]]:
    """Select all existing quiz types from the `quiz_types` table."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            SELECT *
            FROM quiz_types;
            """
        )

        return cursor.fetchall()


def check_if_quiz_type_exists(quiz_type: str) -> bool:
    """Query database to check if `quiz_type` is present in the `quiz_types` table."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            SELECT COUNT(quiz_types.class_type)
            FROM quiz_types
            WHERE quiz_types.class_type = ?;
            """,
            (quiz_type,),
        )

        return cursor.fetchone()[0] >= 1


def select_quiz_str_to_quiz_id(quiz_type: str) -> int:
    """Convert a quiz str to quiz id."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            SELECT id
            FROM quiz_types
            WHERE quiz_types.class_type = ?;
            """,
            (quiz_type,),
        )

        return cursor.fetchone()[0]


def add_quiz_type(quiz_type: str) -> int:
    """Insert a new quiz type to the `quiz_types` table using a `type` string."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            INSERT INTO quiz_types (class_type)
            VALUES (?)
            RETURNING id;
            """,
            (quiz_type,),
        )

        return cursor.fetchone()[0]


def remove_quiz_type(quiz_type: str) -> bool:
    """Delete an existing quiz type from the `quiz_types` table using a `type` string."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            DELETE FROM quiz_types
            WHERE quiz_types.class_type = ?
            RETURNING *;
            """,
            (quiz_type,),
        )

        return len(cursor.fetchall()) >= 1


def select_quiz_settings(quiz_type: str) -> tuple[int, int, int]:
    """"""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            SELECT qs.id, qs.length, qs.min_correct
            FROM quiz_settings AS qs
            LEFT JOIN quiz_types AS qt ON qs.quiz_type = qt.id
            WHERE qt.class_type = ?;
            """,
            (quiz_type,),
        )

        return cursor.fetchone()


def add_quiz_settings(quiz_id: int, quiz_length: int, quiz_min_correct: int) -> None:
    """"""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            INSERT INTO quiz_settings (quiz_type, length, min_correct)
            VALUES (?, ?, ?);
            """,
            (quiz_id, quiz_length, quiz_min_correct),
        )


def remove_quiz_settings(quiz_id: int) -> bool:
    """"""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            DELETE FROM quiz_settings
            WHERE quiz_settings.id = ?
            RETURNING *;
            """,
            (quiz_id,),
        )

        return len(cursor.fetchall()) >= 1


def edit_quiz_settings_length(quiz_length: int, quiz_id: int) -> None:
    """"""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            UPDATE quiz_settings
            SET length = ?
            WHERE quiz_type = ?;
            """,
            (quiz_length, quiz_id),
        )


def edit_quiz_settings_min_correct(quiz_min_correct: int, quiz_id: int) -> None:
    """"""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
            UPDATE quiz_settings
            SET min_correct = ?
            WHERE quiz_type = ?;
            """,
            (quiz_min_correct, quiz_id),
        )
