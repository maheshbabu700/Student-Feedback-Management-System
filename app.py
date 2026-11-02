
"""
app.py - Integrated College Student Feedback Management System.

Member 1: Student feedback form
Member 2: Feedback API and database integration
Member 3: Admin login, dashboard, records and reports
"""

import os
import re
import secrets
import hmac
import unicodedata
from functools import wraps
from math import ceil

from flask import (
    Flask, jsonify, render_template, request,
    redirect, url_for, session
)
from werkzeug.security import generate_password_hash, check_password_hash

import database


# ============================================================
# VALIDATION SETTINGS - MEMBER 2
# ============================================================

FACULTY_ID_PATTERN = re.compile(r"^F\d{3,}$")
COURSE_ID_PATTERN = re.compile(r"^C\d{3,}$")
STUDENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{4,20}$")

NAME_MIN_LENGTH, NAME_MAX_LENGTH = 2, 100
NAME_EXTRA_CHARACTERS = " .'-\u2019"
COMMENTS_MAX_LENGTH = 1000

DEFAULT_CORS_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500"
]


def is_valid_name(name):
    """Validate student names using Unicode letters."""
    if not name or not unicodedata.category(name[0]).startswith("L"):
        return False

    return all(
        unicodedata.category(ch)[0] in ("L", "M")
        or ch in NAME_EXTRA_CHARACTERS
        for ch in name
    )


# ============================================================
# APPLICATION FACTORY
# ============================================================

def create_app(test_config=None):

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-only-change-this-secret-key"
    )

    app.config["DATABASE"] = database.DEFAULT_DB_PATH
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

    app.config["DEFAULT_PAGE_SIZE"] = 100
    app.config["MAX_PAGE_SIZE"] = 500

    app.config["EXPOSE_STUDENT_DETAILS"] = (
        os.environ.get("EXPOSE_STUDENT_DETAILS") == "1"
    )

    app.config["ADMIN_USERNAME"] = os.environ.get(
        "ADMIN_USERNAME", "admin"
    )

    admin_password = os.environ.get(
        "ADMIN_PASSWORD", "Admin@12345"
    )

    app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash(
        admin_password
    )

    env_origins = os.environ.get("CORS_ORIGINS")

    app.config["CORS_ORIGINS"] = (
        [origin.strip() for origin in env_origins.split(",") if origin.strip()]
        if env_origins else DEFAULT_CORS_ORIGINS
    )

    if test_config:
        app.config.update(test_config)

    # Use the existing Member 2 database.
    database.init_db(app.config["DATABASE"])

    # ========================================================
    # COMMON HELPERS
    # ========================================================

    def error_response(message, status, errors=None):
        body = {
            "success": False,
            "message": message
        }

        if errors:
            body["errors"] = errors

        return jsonify(body), status

    def validate_feedback(data):
        """Validate student feedback submitted through the API."""

        errors = {}
        clean = {}

        for field in (
            "student_name",
            "student_id",
            "faculty_id",
            "course_id",
            "comments"
        ):
            if field not in data or data[field] is None:
                errors[field] = "This field is required."

            elif not isinstance(data[field], str):
                errors[field] = "Must be text."

            else:
                clean[field] = data[field].strip()

                if clean[field] == "":
                    errors[field] = "Cannot be blank."

        if "student_name" not in errors:
            length = len(clean["student_name"])

            if not NAME_MIN_LENGTH <= length <= NAME_MAX_LENGTH:
                errors["student_name"] = (
                    "Must be %d to %d characters."
                    % (NAME_MIN_LENGTH, NAME_MAX_LENGTH)
                )

            elif not is_valid_name(clean["student_name"]):
                errors["student_name"] = (
                    "Use letters only (spaces, dots, hyphens "
                    "and apostrophes are allowed)."
                )

        if "student_id" not in errors:
            if not STUDENT_ID_PATTERN.fullmatch(clean["student_id"]):
                errors["student_id"] = (
                    "Use 4 to 20 letters, numbers or hyphens."
                )

        if "faculty_id" not in errors:
            if not FACULTY_ID_PATTERN.fullmatch(clean["faculty_id"]):
                errors["faculty_id"] = (
                    "Invalid faculty ID format (example: F101)."
                )

        if "course_id" not in errors:
            if not COURSE_ID_PATTERN.fullmatch(clean["course_id"]):
                errors["course_id"] = (
                    "Invalid course ID format (example: C201)."
                )

        if "comments" not in errors:
            if len(clean["comments"]) > COMMENTS_MAX_LENGTH:
                errors["comments"] = (
                    "Must be %d characters or fewer."
                    % COMMENTS_MAX_LENGTH
                )

        rating = data.get("rating")

        if "rating" not in data or rating is None:
            errors["rating"] = "This field is required."

        elif isinstance(rating, bool) or not isinstance(rating, int):
            errors["rating"] = "Must be a whole number from 1 to 5."

        elif not 1 <= rating <= 5:
            errors["rating"] = "Must be between 1 and 5."

        else:
            clean["rating"] = rating

        return clean, errors

    def parse_int_arg(name, default, minimum, maximum):
        raw = request.args.get(name)

        if raw is None:
            return default

        if not re.fullmatch(r"\d{1,9}", raw):
            return None

        value = int(raw)

        return value if minimum <= value <= maximum else None

    # ========================================================
    # ADMIN AUTHENTICATION AND CSRF PROTECTION
    # ========================================================

    def login_required(view_function):
        """Allow access only to authenticated administrators."""

        @wraps(view_function)
        def wrapped_view(*args, **kwargs):

            if not session.get("admin_logged_in"):
                return redirect(url_for("login"))

            return view_function(*args, **kwargs)

        return wrapped_view

    def get_csrf_token():
        """Create or retrieve the current session's CSRF token."""

        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)

        return session["csrf_token"]

    @app.context_processor
    def inject_template_helpers():
        return {
            "csrf_token": get_csrf_token
        }

    @app.before_request
    def protect_admin_forms():
        """
        Validate CSRF tokens on admin form submissions.
        The student JSON API is intentionally excluded.
        """

        if request.method == "POST" and request.path in (
            "/login",
            "/logout"
        ):
            submitted_token = request.form.get("csrf_token", "")
            stored_token = session.get("csrf_token", "")

            if (
                not submitted_token
                or not stored_token
                or not hmac.compare_digest(
                    submitted_token, stored_token
                )
            ):
                return (
                    "Invalid or missing CSRF token. "
                    "Please refresh the page and try again.",
                    400
                )

    # ========================================================
    # CORS - MEMBER 2
    # ========================================================

    @app.after_request
    def add_cors_headers(response):

        origin = request.headers.get("Origin")

        if origin and origin in app.config["CORS_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type"
            )
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, OPTIONS"
            )

        return response

    # ========================================================
    # MEMBER 1 - STUDENT FEEDBACK FORM
    # ========================================================

    @app.get("/")
    def feedback_page():
        return render_template("feedback.html")

    # ========================================================
    # MEMBER 2 - STUDENT FEEDBACK API
    # ========================================================

    @app.get("/api/health")
    def health():

        return jsonify({
            "success": True,
            "message": "Backend is running",
            "status": "ok"
        }), 200

    @app.post("/api/feedback")
    def submit_feedback():

        if not request.is_json:
            return error_response(
                "Content-Type must be application/json.",
                415
            )

        data = request.get_json(silent=True)

        if data is None:
            return error_response(
                "Request body is not valid JSON.",
                400
            )

        if not isinstance(data, dict):
            return error_response(
                "Request body must be a JSON object.",
                400
            )

        clean, errors = validate_feedback(data)

        if errors:
            return error_response(
                "Invalid feedback data",
                422,
                errors
            )

        try:
            feedback_id = database.insert_feedback(
                app.config["DATABASE"],
                **clean
            )

        except database.DatabaseError:
            app.logger.exception(
                "Database error while saving feedback"
            )

            return error_response(
                "Feedback could not be saved. Please try again later.",
                500
            )

        return jsonify({
            "success": True,
            "message": "Feedback saved successfully",
            "feedback_id": feedback_id
        }), 201

    @app.get("/api/feedback")
    def list_feedback():

        # Development API: student details are hidden by default.
        limit = parse_int_arg(
            "limit",
            app.config["DEFAULT_PAGE_SIZE"],
            1,
            app.config["MAX_PAGE_SIZE"]
        )

        offset = parse_int_arg(
            "offset",
            0,
            0,
            10**9
        )

        if limit is None or offset is None:
            return error_response(
                "Invalid limit or offset.",
                400
            )

        try:
            rows, total = database.get_feedback(
                app.config["DATABASE"],
                limit=limit,
                offset=offset,
                faculty_id=request.args.get(
                    "faculty_id", ""
                ).strip() or None,
                course_id=request.args.get(
                    "course_id", ""
                ).strip() or None
            )

        except database.DatabaseError:
            app.logger.exception(
                "Database error while reading feedback"
            )

            return error_response(
                "Feedback could not be retrieved. Please try again later.",
                500
            )

        if not app.config["EXPOSE_STUDENT_DETAILS"]:
            for row in rows:
                row.pop("student_name", None)
                row.pop("student_id", None)

        return jsonify({
            "success": True,
            "message": "Feedback retrieved successfully",
            "count": len(rows),
            "total": total,
            "limit": limit,
            "offset": offset,
            "feedback": rows
        }), 200

    # ========================================================
    # MEMBER 3 - ADMIN LOGIN
    # ========================================================

    @app.route("/login", methods=["GET", "POST"])
    def login():

        if session.get("admin_logged_in"):
            return redirect(url_for("dashboard"))

        error = None

        if request.method == "POST":

            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            correct_username = (
                username == app.config["ADMIN_USERNAME"]
            )

            correct_password = check_password_hash(
                app.config["ADMIN_PASSWORD_HASH"],
                password
            )

            if correct_username and correct_password:

                session.clear()
                session["admin_logged_in"] = True
                session["admin_username"] = username
                session.permanent = True

                return redirect(url_for("dashboard"))

            error = "Invalid username or password."

        return render_template(
            "login.html",
            error=error
        )

    # ========================================================
    # MEMBER 3 - ADMIN DASHBOARD
    # ========================================================

    @app.get("/dashboard")
    @login_required
    def dashboard():

        db_path = app.config["DATABASE"]

        try:
            summary = database.get_dashboard_summary(db_path)

            faculty_report = database.get_report_by(
                "faculty_id", db_path
            )

            course_report = database.get_report_by(
                "course_id", db_path
            )

            rating_distribution = database.get_rating_distribution(
                db_path
            )

        except database.DatabaseError:
            app.logger.exception(
                "Could not load admin dashboard"
            )

            return "Unable to load dashboard data.", 500

        return render_template(
            "dashboard.html",
            summary=summary,
            faculty_report=faculty_report,
            course_report=course_report,
            rating_distribution=rating_distribution
        )

    # ========================================================
    # MEMBER 3 - FEEDBACK RECORDS
    # ========================================================

    @app.get("/feedback")
    @login_required
    def feedback():

        db_path = app.config["DATABASE"]

        search = request.args.get("search", "").strip()
        selected_faculty = request.args.get(
            "faculty_id", ""
        ).strip()

        selected_course = request.args.get(
            "course_id", ""
        ).strip()

        selected_rating = request.args.get(
            "rating", ""
        ).strip()

        page = parse_int_arg("page", 1, 1, 10**6)

        if page is None:
            return "Invalid page number.", 400

        if selected_rating and selected_rating not in (
            "1", "2", "3", "4", "5"
        ):
            selected_rating = ""

        per_page = 10

        try:
            filter_options = database.get_filter_options(db_path)

            records, total = database.get_feedback_records(
                db_path=db_path,
                search=search,
                faculty_id=selected_faculty,
                course_id=selected_course,
                rating=selected_rating,
                page=page,
                per_page=per_page
            )

        except database.DatabaseError:
            app.logger.exception(
                "Could not load feedback records"
            )

            return "Unable to load feedback records.", 500

        total_pages = max(1, ceil(total / per_page))

        # If a user requests a page beyond the available pages,
        # display the last available page.
        if page > total_pages:
            return redirect(
                url_for(
                    "feedback",
                    search=search,
                    faculty_id=selected_faculty,
                    course_id=selected_course,
                    rating=selected_rating,
                    page=total_pages
                )
            )

        return render_template(
            "feedback_records.html",
            records=records,
            total=total,
            search=search,
            selected_faculty=selected_faculty,
            selected_course=selected_course,
            selected_rating=selected_rating,
            faculties=filter_options["faculties"],
            courses=filter_options["courses"],
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    # ========================================================
    # MEMBER 3 - REPORTS
    # ========================================================

    @app.get("/reports")
    @login_required
    def reports():

        db_path = app.config["DATABASE"]

        try:
            faculty_report = database.get_report_by(
                "faculty_id", db_path
            )

            course_report = database.get_report_by(
                "course_id", db_path
            )

            rating_distribution = database.get_rating_distribution(
                db_path
            )

        except database.DatabaseError:
            app.logger.exception(
                "Could not load feedback reports"
            )

            return "Unable to load feedback reports.", 500

        return render_template(
            "reports.html",
            faculty_report=faculty_report,
            course_report=course_report,
            rating_distribution=rating_distribution
        )

    # ========================================================
    # MEMBER 3 - ADMIN LOGOUT
    # ========================================================

    @app.post("/logout")
    @login_required
    def logout():

        session.clear()

        return redirect(url_for("login"))

    # ========================================================
    # JSON ERROR HANDLERS - MEMBER 2
    # ========================================================

    @app.errorhandler(404)
    def not_found(_error):
        return error_response(
            "Endpoint not found.",
            404
        )

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return error_response(
            "Method not allowed for this endpoint.",
            405
        )

    @app.errorhandler(413)
    def too_large(_error):
        return error_response(
            "Request body is too large.",
            413
        )

    @app.errorhandler(500)
    def server_error(_error):
        return error_response(
            "Internal server error.",
            500
        )

    return app


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    create_app().run(
        host="127.0.0.1",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )
