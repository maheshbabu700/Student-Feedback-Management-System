
"""
database.py - SQLite helpers for the Integrated College Student Feedback System.

Preserves Member 2 database operations and adds Member 3 admin dashboard queries.
All admin queries use the same database file as the student feedback API.
"""

import os
import sqlite3
from contextlib import closing

# Default database location
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
    """Raised when a database operation fails."""


def get_connection(db_path):
    """Open a SQLite connection with dictionary-like rows."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path):
    """Create the database folder and feedback table if necessary."""
    try:
        folder = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(folder, exist_ok=True)

        with closing(get_connection(db_path)) as connection:
            with connection:
                connection.execute(CREATE_TABLE_SQL)

    except (sqlite3.Error, OSError) as error:
        raise DatabaseError(
            "Could not initialise the database: " + str(error)
        ) from error


# ============================================================
# MEMBER 2 - EXISTING STUDENT FEEDBACK OPERATIONS
# ============================================================

def insert_feedback(
    db_path,
    student_name,
    student_id,
    faculty_id,
    course_id,
    rating,
    comments
):
    """Save one feedback record and return its new ID."""

    sql = """
        INSERT INTO feedback
        (student_name, student_id, faculty_id, course_id, rating, comments)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    values = (
        student_name,
        student_id,
        faculty_id,
        course_id,
        rating,
        comments
    )

    try:
        with closing(get_connection(db_path)) as connection:
            with connection:
                cursor = connection.execute(sql, values)
                return cursor.lastrowid

    except sqlite3.Error as error:
        raise DatabaseError(
            "Could not save feedback: " + str(error)
        ) from error


def get_feedback(
    db_path,
    limit=100,
    offset=0,
    faculty_id=None,
    course_id=None
):
    """
    Return (rows, total).
    Used by Member 2's existing GET /api/feedback endpoint.
    """

    conditions = []
    params = []

    if faculty_id:
        conditions.append("faculty_id = ?")
        params.append(faculty_id)

    if course_id:
        conditions.append("course_id = ?")
        params.append(course_id)

    where = (
        " WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    try:
        with closing(get_connection(db_path)) as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM feedback" + where,
                params
            ).fetchone()[0]

            rows = connection.execute(
                """
                SELECT id, student_name, student_id, faculty_id,
                       course_id, rating, comments, created_at
                FROM feedback
                """
                + where
                + " ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [limit, offset]
            ).fetchall()

        return [dict(row) for row in rows], total

    except sqlite3.Error as error:
        raise DatabaseError(
            "Could not read feedback: " + str(error)
        ) from error


# ============================================================
# MEMBER 3 - ADMIN DASHBOARD OPERATIONS
# ============================================================

def get_dashboard_summary(db_path=DEFAULT_DB_PATH):
    """Return the summary statistics displayed on the dashboard."""

    sql = """
        SELECT
            COUNT(*) AS total_submissions,
            COALESCE(ROUND(AVG(rating), 2), 0) AS average_rating,
            COUNT(DISTINCT faculty_id) AS total_faculty,
            COUNT(DISTINCT course_id) AS total_courses
        FROM feedback
    """

    try:
        with closing(get_connection(db_path)) as connection:
            row = connection.execute(sql).fetchone()

        return dict(row)

    except sqlite3.Error as error:
        raise DatabaseError(
            "Could not retrieve dashboard summary: " + str(error)
        ) from error


def get_filter_options(db_path=DEFAULT_DB_PATH):
    """Return distinct faculty and course IDs for feedback filters."""

    try:
        with closing(get_connection(db_path)) as connection:
            faculties = connection.execute(
                """
                SELECT DISTINCT faculty_id
                FROM feedback
                ORDER BY faculty_id
                """
            ).fetchall()

            courses = connection.execute(
                """
                SELECT DISTINCT course_id
                FROM feedback
                ORDER BY course_id
                """
            ).fetchall()

        return {
            "faculties": [row["faculty_id"] for row in faculties],
            "courses": [row["course_id"] for row in courses]
        }

    except sqlite3.Error as error:
        raise DatabaseError(
            "Could not retrieve filter options: " + str(error)
        ) from error


def _escape_like(value):
    """Escape SQL LIKE wildcard characters in user search text."""
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def get_feedback_records(
    db_path=DEFAULT_DB_PATH,
    search="",
    faculty_id="",
    course_id="",
    rating="",
    page=1,
    per_page=10
):
    """
    Return (records, total) for the admin feedback records page.
    Supports search, filters and pagination.
    """

    conditions = []
    params = []

    if search:
        search_value = "%" + _escape_like(search.strip()) + "%"
        conditions.append(
            """
            (
                student_name LIKE ? ESCAPE '\\'
                OR student_id LIKE ? ESCAPE '\\'
                OR comments LIKE ? ESCAPE '\\'
            )
            """
        )
        params.extend([search_value, search_value, search_value])

    if faculty_id:
        conditions.append("faculty_id = ?")
        params.append(faculty_id)

    if course_id:
        conditions.append("course_id = ?")
        params.append(course_id)

    if rating:
        conditions.append("rating = ?")
        params.append(int(rating))

    where = (
        " WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    page = max(1, int(page))
    per_page = max(1, int(per_page))
    offset = (page - 1) * per_page

    try:
        with closing(get_connection(db_path)) as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM feedback" + where,
                params
            ).fetchone()[0]

            rows = connection.execute(
                """
                SELECT id, student_name, student_id, faculty_id,
                       course_id, rating, comments, created_at
                FROM feedback
                """
                + where
                + " ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [per_page, offset]
            ).fetchall()

        return [dict(row) for row in rows], total

    except (sqlite3.Error, ValueError) as error:
        raise DatabaseError(
            "Could not retrieve feedback records: " + str(error)
        ) from error


def get_report_by(column, db_path=DEFAULT_DB_PATH):
    """
    Return submission count and average rating grouped by faculty or course.
    Each result contains: category, submission_count, average_rating.
    """

    allowed_columns = ("faculty_id", "course_id")

    if column not in allowed_columns:
        raise ValueError("Invalid report column.")

    sql = f"""
        SELECT
            {column} AS category,
            COUNT(*) AS submission_count,
            ROUND(AVG(rating), 2) AS average_rating
        FROM feedback
        GROUP BY {column}
        ORDER BY {column}
    """

    try:
        with closing(get_connection(db_path)) as connection:
            rows = connection.execute(sql).fetchall()

        return [dict(row) for row in rows]

    except sqlite3.Error as error:
        raise DatabaseError(
            "Could not retrieve report: " + str(error)
        ) from error


def get_rating_distribution(db_path=DEFAULT_DB_PATH):
    """Return the number of feedback submissions for each rating (1-5)."""

    sql = """
        SELECT rating, COUNT(*) AS count
        FROM feedback
        GROUP BY rating
        ORDER BY rating
    """

    try:
        with closing(get_connection(db_path)) as connection:
            rows = connection.execute(sql).fetchall()

        counts = {row["rating"]: row["count"] for row in rows}

        return [
            {"rating": number, "count": counts.get(number, 0)}
            for number in range(1, 6)
        ]

    except sqlite3.Error as error:
        raise DatabaseError(
            "Could not retrieve rating distribution: " + str(error)
        ) from error
