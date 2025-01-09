import sqlite3 as sql
import contextlib
import os

def create_tables_if_not_exist() -> None:
    """Init SQL statements to create required tables if they do not exist."""
    with contextlib.closing(
        sql.connect(os.getenv("SQLITE_DATABASE"))
    ) as conn:  # auto-closes
        with conn:  # auto-commits
            with contextlib.closing(conn.cursor()) as cursor:  # auto-closes
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS managers (
                        id INTEGER PRIMARY KEY,
                        discord_id INTEGER UNIQUE NOT NULL,
                        added_at TEXT NOT NULL DEFAULT current_timestamp
                    );
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS quiz_question_bank (
                        id INTEGER PRIMARY KEY,
                        question_text TEXT NOT NULL,
                        created_by INTEGER UNIQUE NOT NULL,
                        created_at TEXT NOT NULL DEFAULT current_timestamp
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
    with contextlib.closing(
        sql.connect(os.getenv("SQLITE_DATABASE"))
    ) as conn:  # auto-closes
        with conn:  # auto-commits
            with contextlib.closing(conn.cursor()) as cursor:  # auto-closes
                cursor.execute(
                """
                SELECT TOP 1 managers.discord_id
                FROM managers
                WHERE managers.discord_id = ?
                """,
                user_id
                )

                return (user_id == cursor.fetchone())