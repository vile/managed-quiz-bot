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
            CREATE TABLE IF NOT EXISTS quiz_question_bank (
                id INTEGER PRIMARY KEY,
                question_text TEXT NOT NULL,
                created_by INTEGER UNIQUE NOT NULL,
                created_at INTEGER NOT NULL DEFAULT (unixepoch('now'))
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


def check_if_manager_exists(user_id: int) -> bool:
    """Query database to check if `user_id` is present in the `managers` database."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
        SELECT COUNT(managers.discord_id)
        FROM managers
        WHERE managers.discord_id = ?
        """,
            (user_id,),
        )

        return cursor.fetchone()[0] >= 1


def add_new_manager(manager_id: int, caller_id: int) -> None:
    """Insert a new manager into the `managers` database using their Discord ID."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
        INSERT INTO managers (discord_id, added_by)
        VALUES (?, ?);
        """,
            (manager_id, caller_id),
        )


def remove_current_manager(manager_id: int) -> bool:
    """Delete an existing manager from the `managers` database using their Discord ID."""
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


def select_all_managers() -> list[int]:
    """Select all existing bot managers."""
    with get_db_context() as (_, cursor):
        cursor.execute(
            """
        SELECT *
        FROM managers;
        """
        )

        return cursor.fetchall()
