"""
app.py - Integrated College Student Feedback System (Member 1 form + Member 2 backend).

Endpoints:
    GET  /              -> the student feedback form
    GET  /api/health    -> is the server running?
    POST /api/feedback  -> validate and save one feedback record
    GET  /api/feedback  -> list saved feedback (DEVELOPMENT ONLY, see README)

Every response is JSON:
    success: {"success": true,  "message": "...", ...extra data...}
    error:   {"success": false, "message": "...", "errors": {field: reason}}   ("errors" only for validation)
"""

import os
import re
import unicodedata

from flask import Flask, jsonify, render_template, request

import database

# ---- Validation rules (change here if the team agrees on a different format) ----
FACULTY_ID_PATTERN = re.compile(r"^F\d{3,}$")        # e.g. F101  (same as the Member 1 form)
COURSE_ID_PATTERN = re.compile(r"^C\d{3,}$")         # e.g. C201
STUDENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{4,20}$")  # same rule as the Member 1 form
NAME_MIN_LENGTH, NAME_MAX_LENGTH = 2, 100
NAME_EXTRA_CHARACTERS = " .'-\u2019"                # besides letters: space . ' - and the curly apostrophe
COMMENTS_MAX_LENGTH = 1000                           # same as maxlength in the Member 1 form

# Origins allowed to call the API from a browser (needed when the frontend is served separately).
# VS Code Live Server uses port 5500. Add more here, or set the CORS_ORIGINS environment variable.
DEFAULT_CORS_ORIGINS = ["http://127.0.0.1:5500", "http://localhost:5500"]


def is_valid_name(name):
    """True if name starts with a letter and has only letters (any language, with accents and
    combining marks such as Telugu vowel signs), spaces, dots, hyphens and apostrophes.
    This matches the rule in the form's feedback.js, so digits and HTML like "<b>" are rejected."""
    if not name or not unicodedata.category(name[0]).startswith("L"):
        return False
    return all(
        unicodedata.category(ch)[0] in ("L", "M") or ch in NAME_EXTRA_CHARACTERS
        for ch in name
    )


def create_app(test_config=None):
    """Application factory. Tests pass test_config to use a temporary database."""
    app = Flask(__name__)
    app.config["DATABASE"] = database.DEFAULT_DB_PATH
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024      # requests above 16 KB are rejected
    app.config["DEFAULT_PAGE_SIZE"] = 100
    app.config["MAX_PAGE_SIZE"] = 500
    # Student name/ID are hidden from GET /api/feedback unless this is switched on (dev only).
    app.config["EXPOSE_STUDENT_DETAILS"] = os.environ.get("EXPOSE_STUDENT_DETAILS") == "1"
    env_origins = os.environ.get("CORS_ORIGINS")
    app.config["CORS_ORIGINS"] = (
        [o.strip() for o in env_origins.split(",") if o.strip()] if env_origins else DEFAULT_CORS_ORIGINS
    )
    if test_config:
        app.config.update(test_config)

    database.init_db(app.config["DATABASE"])

    # ---------------------------------------------------------------- helpers
    def error_response(message, status, errors=None):
        body = {"success": False, "message": message}
        if errors:
            body["errors"] = errors
        return jsonify(body), status

    def validate_feedback(data):
        """Return (clean_data, errors). errors is empty when everything is valid."""
        errors = {}
        clean = {}

        # Required text fields must be present and must be strings
        for field in ("student_name", "student_id", "faculty_id", "course_id", "comments"):
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
                errors["student_name"] = "Must be %d to %d characters." % (NAME_MIN_LENGTH, NAME_MAX_LENGTH)
            elif not is_valid_name(clean["student_name"]):
                errors["student_name"] = "Use letters only (spaces, dots, hyphens and apostrophes are allowed)."

        if "student_id" not in errors and not STUDENT_ID_PATTERN.match(clean["student_id"]):
            errors["student_id"] = "Use 4 to 20 letters, numbers or hyphens (no spaces)."

        if "faculty_id" not in errors and not FACULTY_ID_PATTERN.match(clean["faculty_id"]):
            errors["faculty_id"] = "Invalid faculty ID format (expected something like F101)."

        if "course_id" not in errors and not COURSE_ID_PATTERN.match(clean["course_id"]):
            errors["course_id"] = "Invalid course ID format (expected something like C201)."

        if "comments" not in errors and len(clean["comments"]) > COMMENTS_MAX_LENGTH:
            errors["comments"] = "Must be %d characters or fewer." % COMMENTS_MAX_LENGTH

        # Rating: must be a real JSON integer 1-5. bool is a subclass of int in Python, so exclude it.
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
        """Read an integer query parameter, or return None if it is invalid."""
        raw = request.args.get(name)
        if raw is None:
            return default
        if not re.fullmatch(r"\d{1,9}", raw):
            return None
        value = int(raw)
        return value if minimum <= value <= maximum else None

    # ------------------------------------------------------------------- CORS
    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin and origin in app.config["CORS_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    # ----------------------------------------------------------------- routes
    @app.get("/")
    def feedback_page():
        # Serves the Member 1 form. Because the page and the API come from the same
        # address, the browser needs no CORS permission to call /api/feedback.
        return render_template("feedback.html")

    @app.get("/api/health")
    def health():
        return jsonify({"success": True, "message": "Backend is running", "status": "ok"}), 200

    @app.post("/api/feedback")
    def submit_feedback():
        if not request.is_json:
            return error_response("Content-Type must be application/json.", 415)

        data = request.get_json(silent=True)      # None if the JSON is malformed
        if data is None:
            return error_response("Request body is not valid JSON.", 400)
        if not isinstance(data, dict):
            return error_response("Request body must be a JSON object.", 400)

        clean, errors = validate_feedback(data)
        if errors:
            return error_response("Invalid feedback data", 422, errors)

        try:
            feedback_id = database.insert_feedback(app.config["DATABASE"], **clean)
        except database.DatabaseError:
            app.logger.exception("Database error while saving feedback")
            return error_response("Feedback could not be saved. Please try again later.", 500)

        # Only reached after the INSERT has been committed
        return jsonify({"success": True, "message": "Feedback saved successfully",
                        "feedback_id": feedback_id}), 201

    @app.get("/api/feedback")
    def list_feedback():
        # DEVELOPMENT ONLY: no authentication yet. See README before any deployment.
        limit = parse_int_arg("limit", app.config["DEFAULT_PAGE_SIZE"], 1, app.config["MAX_PAGE_SIZE"])
        offset = parse_int_arg("offset", 0, 0, 10**9)
        if limit is None or offset is None:
            return error_response(
                "limit must be 1-%d and offset must be 0 or more." % app.config["MAX_PAGE_SIZE"], 400)

        try:
            rows, total = database.get_feedback(
                app.config["DATABASE"], limit=limit, offset=offset,
                faculty_id=request.args.get("faculty_id", "").strip() or None,
                course_id=request.args.get("course_id", "").strip() or None,
            )
        except database.DatabaseError:
            app.logger.exception("Database error while reading feedback")
            return error_response("Feedback could not be retrieved. Please try again later.", 500)

        if not app.config["EXPOSE_STUDENT_DETAILS"]:
            for row in rows:
                row.pop("student_name", None)
                row.pop("student_id", None)

        return jsonify({"success": True, "message": "Feedback retrieved successfully",
                        "count": len(rows), "total": total, "limit": limit, "offset": offset,
                        "feedback": rows}), 200

    # ------------------------------------------------------- JSON error pages
    @app.errorhandler(404)
    def not_found(_error):
        return error_response("Endpoint not found.", 404)

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return error_response("Method not allowed for this endpoint.", 405)

    @app.errorhandler(413)
    def too_large(_error):
        return error_response("Request body is too large.", 413)

    @app.errorhandler(500)
    def server_error(_error):
        return error_response("Internal server error.", 500)

    return app


if __name__ == "__main__":
    # The app (and the real database file) is only created when you run this file directly,
    # so importing create_app in tests never touches real data.
    # 127.0.0.1 = only this computer can connect. Set FLASK_DEBUG=1 for auto-reload while developing.
    create_app().run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
