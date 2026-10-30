"""
database.py - SQLite helpers for the College Student Feedback System (Member 2).

Uses Python's built-in sqlite3 module. Every query is parameterized
(the ? placeholders), so user input is never pasted into SQL text.
"""

import os
import sqlite3
from contextlib import closing

# Default database location: member2-backend/database/feedback.db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "database", "feedback.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS feedback (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT    NOT NULL CHECK (length(trim(student_name)) > 0),
    student_id   TEXT    NOT NULL CHECK (length(trim(student_id)) > 0),
    faculty_id   TEXT    NOT NULL CHECK (length(trim(faculty_id)) > 0),
    course_id    TEXT    NOT NULL CHECK (length(trim(course_id)) > 0),
    rating       INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comments     TEXT    NOT NULL CHECK (length(trim(comments)) > 0),
    created_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class DatabaseError(Exception):
    """Raised when a database operation fails. app.py turns it into a 500 response."""


def get_connection(db_path):
    """Open a connection. Rows can be read like dictionaries (row["rating"])."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path):
    """Create the database folder and the feedback table if they do not exist yet."""
    try:
        folder = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(folder, exist_ok=True)
        # "with connection" = one transaction (commit on success, rollback on error)
        with closing(get_connection(db_path)) as connection:
            with connection:
                connection.execute(CREATE_TABLE_SQL)
    except (sqlite3.Error, OSError) as error:
        raise DatabaseError("Could not initialise the database: " + str(error)) from error


def insert_feedback(db_path, student_name, student_id, faculty_id, course_id, rating, comments):
    """Save one feedback row inside a transaction. Returns the new row id."""
    sql = (
        "INSERT INTO feedback "
        "(student_name, student_id, faculty_id, course_id, rating, comments) "
        "VALUES (?, ?, ?, ?, ?, ?)"
    )
    values = (student_name, student_id, faculty_id, course_id, rating, comments)
    try:
        with closing(get_connection(db_path)) as connection:
            with connection:  # commits only if the insert succeeds, otherwise rolls back
                cursor = connection.execute(sql, values)
                return cursor.lastrowid
    except sqlite3.Error as error:
        raise DatabaseError("Could not save feedback: " + str(error)) from error


def get_feedback(db_path, limit=100, offset=0, faculty_id=None, course_id=None):
    """
    Return (rows, total). rows is a list of dictionaries, newest first.
    total is the number of records matching the filters (ignoring limit/offset).
    """
    conditions = []
    params = []
    if faculty_id:
        conditions.append("faculty_id = ?")
        params.append(faculty_id)
    if course_id:
        conditions.append("course_id = ?")
        params.append(course_id)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    try:
        with closing(get_connection(db_path)) as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM feedback" + where, params
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT id, student_name, student_id, faculty_id, course_id, "
                "rating, comments, created_at FROM feedback" + where +
                " ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
        return [dict(row) for row in rows], total
    except sqlite3.Error as error:
        raise DatabaseError("Could not read feedback: " + str(error)) from error
