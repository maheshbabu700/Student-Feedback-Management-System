"""
Tests for the Member 2 backend. Run from the member2-backend folder with:

    python -m unittest discover -s tests -v

Every test uses its own temporary database, so real data in database/feedback.db is never touched.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

# Make "import app" / "import database" work when tests are run from member2-backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
from app import create_app


def valid_payload(**overrides):
    payload = {
        "student_name": "Ravi Kumar",
        "student_id": "22A91A0501",
        "faculty_id": "F101",
        "course_id": "C201",
        "rating": 4,
        "comments": "Clear explanations and helpful examples.",
    }
    payload.update(overrides)
    return payload


class BackendTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "nested", "test_feedback.db")  # folder does not exist yet
        self.app = create_app({"TESTING": True, "DATABASE": self.db_path})
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def post(self, payload):
        return self.client.post("/api/feedback", json=payload)

    def row_count(self):
        connection = sqlite3.connect(self.db_path)
        try:
            return connection.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        finally:
            connection.close()


class TestDatabaseInitialisation(BackendTestCase):  # 1
    def test_database_file_and_table_created(self):
        self.assertTrue(os.path.exists(self.db_path))
        connection = sqlite3.connect(self.db_path)
        columns = [row[1] for row in connection.execute("PRAGMA table_info(feedback)")]
        connection.close()
        self.assertEqual(columns, ["id", "student_name", "student_id", "faculty_id",
                                   "course_id", "rating", "comments", "created_at"])

    def test_init_is_safe_to_run_twice(self):
        database.init_db(self.db_path)
        database.init_db(self.db_path)

    def test_database_rejects_bad_rating_directly(self):
        with self.assertRaises(database.DatabaseError):
            database.insert_feedback(self.db_path, "Ravi", "22A91A0501", "F101", "C201", 9, "ok")
        self.assertEqual(self.row_count(), 0)


class TestHealth(BackendTestCase):  # 2
    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertEqual(response.get_json()["status"], "ok")


class TestSubmitValid(BackendTestCase):  # 3, 8
    def test_valid_submission_saved(self):
        response = self.post(valid_payload())
        body = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(body, {"success": True, "message": "Feedback saved successfully", "feedback_id": 1})
        self.assertEqual(self.row_count(), 1)

    def test_values_are_trimmed_and_stored(self):
        self.post(valid_payload(student_name="  Ravi Kumar  ", comments="  Good  "))
        connection = sqlite3.connect(self.db_path)
        row = connection.execute("SELECT student_name, comments, created_at FROM feedback").fetchone()
        connection.close()
        self.assertEqual(row[0], "Ravi Kumar")
        self.assertEqual(row[1], "Good")
        self.assertTrue(row[2])  # timestamp filled in automatically

    def test_sql_injection_text_is_stored_as_plain_text(self):
        evil = "x'); DROP TABLE feedback;--"
        self.assertEqual(self.post(valid_payload(comments=evil)).status_code, 201)
        self.assertEqual(self.row_count(), 1)


class TestMissingFields(BackendTestCase):  # 4
    def test_each_missing_field_rejected(self):
        for field in ("student_name", "student_id", "faculty_id", "course_id", "rating", "comments"):
            with self.subTest(field=field):
                payload = valid_payload()
                del payload[field]
                response = self.post(payload)
                self.assertEqual(response.status_code, 422)
                body = response.get_json()
                self.assertFalse(body["success"])
                self.assertIn(field, body["errors"])
        self.assertEqual(self.row_count(), 0)

    def test_blank_and_wrong_type_fields_rejected(self):
        for field, value in [("student_name", "   "), ("student_id", ""), ("faculty_id", "  "),
                             ("course_id", None), ("student_name", 123), ("faculty_id", ["F101"])]:
            with self.subTest(field=field, value=value):
                self.assertEqual(self.post(valid_payload(**{field: value})).status_code, 422)

    def test_bad_id_formats_rejected(self):
        for field, value in [("faculty_id", "X999"), ("faculty_id", "F1"), ("course_id", "F101"),
                             ("course_id", "C201; DROP"), ("student_id", "ab"), ("student_id", "has space1")]:
            with self.subTest(field=field, value=value):
                self.assertEqual(self.post(valid_payload(**{field: value})).status_code, 422)

    def test_empty_json_object_rejected(self):
        self.assertEqual(self.post({}).status_code, 422)


class TestInvalidRating(BackendTestCase):  # 5
    def test_invalid_ratings_rejected(self):
        for bad in (0, 6, -1, True, False, 4.5, 5.0, "5", "abc", None, [], {}):
            with self.subTest(rating=bad):
                response = self.post(valid_payload(rating=bad))
                self.assertEqual(response.status_code, 422)
                self.assertIn("rating", response.get_json()["errors"])
        self.assertEqual(self.row_count(), 0)

    def test_all_valid_ratings_accepted(self):
        for good in (1, 2, 3, 4, 5):
            self.assertEqual(self.post(valid_payload(rating=good)).status_code, 201)


class TestStudentName(BackendTestCase):
    def test_real_names_in_any_language_are_accepted(self):
        for name in ("Ravi Kumar", "Mary-Ann O'Neil", "K. Ravi", "Mary \u2019Ann", "\u015arinivas Rao",
                     "Jos\u00e9 \u00c1lvarez", "\u0c30\u0c35\u0c3f \u0c15\u0c41\u0c2e\u0c3e\u0c30\u0c4d",
                     "\u0930\u093e\u091c\u0947\u0936 \u0915\u0941\u092e\u093e\u0930"):
            with self.subTest(name=name):
                self.assertEqual(self.post(valid_payload(student_name=name)).status_code, 201)

    def test_digits_symbols_and_html_are_rejected(self):
        for name in ("12345", "Ravi2", "<b>x</b>", "<script>alert(1)</script>", "-Ravi", ".Ravi",
                     "Ravi_Kumar", "Ravi@Kumar", "R", "x" * 101):
            with self.subTest(name=name):
                response = self.post(valid_payload(student_name=name))
                self.assertEqual(response.status_code, 422)
                self.assertIn("student_name", response.get_json()["errors"])
        self.assertEqual(self.row_count(), 0)


class TestComments(BackendTestCase):  # 6
    def test_empty_and_whitespace_comments_rejected(self):
        for bad in ("", "   ", "\n\t  \n"):
            with self.subTest(comments=repr(bad)):
                response = self.post(valid_payload(comments=bad))
                self.assertEqual(response.status_code, 422)
                self.assertIn("comments", response.get_json()["errors"])

    def test_too_long_comments_rejected(self):
        self.assertEqual(self.post(valid_payload(comments="a" * 1001)).status_code, 422)


class TestMalformedRequests(BackendTestCase):  # 7
    def test_malformed_json(self):
        response = self.client.post("/api/feedback", data="{not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_json_that_is_not_an_object(self):
        response = self.client.post("/api/feedback", data="[1, 2]", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_wrong_content_type(self):
        response = self.client.post("/api/feedback", data="student_name=x", content_type="text/plain")
        self.assertEqual(response.status_code, 415)

    def test_oversized_body(self):
        response = self.post(valid_payload(comments="a" * 20000))
        self.assertEqual(response.status_code, 413)

    def test_unknown_route_and_method_return_json(self):
        self.assertEqual(self.client.get("/nope").get_json()["success"], False)
        response = self.client.delete("/api/feedback")
        self.assertEqual(response.status_code, 405)
        self.assertFalse(response.get_json()["success"])


class TestRetrieve(BackendTestCase):  # 9
    def test_empty_list(self):
        body = self.client.get("/api/feedback").get_json()
        self.assertTrue(body["success"])
        self.assertEqual((body["count"], body["total"], body["feedback"]), (0, 0, []))

    def test_saved_feedback_returned_without_student_details(self):
        self.post(valid_payload())
        self.post(valid_payload(faculty_id="F102", course_id="C202", rating=2, comments="Too fast"))
        response = self.client.get("/api/feedback")
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["total"], 2)
        newest = body["feedback"][0]
        self.assertEqual(newest["id"], 2)  # newest first
        self.assertEqual(set(newest), {"id", "faculty_id", "course_id", "rating", "comments", "created_at"})
        self.assertNotIn("student_id", newest)
        self.assertNotIn("student_name", newest)

    def test_student_details_only_when_switched_on(self):
        self.app.config["EXPOSE_STUDENT_DETAILS"] = True
        self.post(valid_payload())
        record = self.client.get("/api/feedback").get_json()["feedback"][0]
        self.assertEqual(record["student_id"], "22A91A0501")

    def test_filters_and_paging(self):
        self.post(valid_payload())
        self.post(valid_payload(faculty_id="F102"))
        self.post(valid_payload(faculty_id="F102"))
        body = self.client.get("/api/feedback?faculty_id=F102&limit=1").get_json()
        self.assertEqual((body["total"], body["count"]), (2, 1))

    def test_invalid_paging_rejected(self):
        for query in ("limit=0", "limit=abc", "limit=99999", "offset=-1"):
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/api/feedback?" + query).status_code, 400)

    def test_filter_value_is_not_executed_as_sql(self):
        self.post(valid_payload())
        body = self.client.get("/api/feedback", query_string={"faculty_id": "F101' OR '1'='1"}).get_json()
        self.assertEqual(body["total"], 0)


class TestDatabaseErrors(BackendTestCase):  # 10
    def test_insert_failure_returns_500_and_no_false_success(self):
        with mock.patch("sqlite3.connect", side_effect=sqlite3.OperationalError("disk I/O error")), \
                self.assertLogs(self.app.logger, level="ERROR"):  # error is logged (and hidden from test output)
            response = self.post(valid_payload())
        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertFalse(body["success"])
        self.assertNotIn("feedback_id", body)
        self.assertNotIn("disk I/O", body["message"])  # internal details are not leaked
        self.assertEqual(self.row_count(), 0)

    def test_read_failure_returns_500(self):
        with mock.patch("sqlite3.connect", side_effect=sqlite3.OperationalError("locked")), \
                self.assertLogs(self.app.logger, level="ERROR"):
            response = self.client.get("/api/feedback")
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.get_json()["success"])

    def test_missing_table_returns_500(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute("DROP TABLE feedback")
        connection.commit()
        connection.close()
        with self.assertLogs(self.app.logger, level="ERROR"):
            response = self.post(valid_payload())
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.get_json()["success"])


class TestIntegratedPage(BackendTestCase):
    def test_form_page_is_served(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        for name in ("student_name", "student_id", "faculty_id", "course_id", "rating", "comments"):
            self.assertIn('name="%s"' % name, html)
        self.assertIn("/static/css/style.css", html)
        self.assertIn("/static/js/feedback.js", html)

    def test_static_files_are_served(self):
        self.assertEqual(self.client.get("/static/css/style.css").status_code, 200)
        self.assertEqual(self.client.get("/static/js/feedback.js").status_code, 200)

    def test_faculty_and_course_ids_in_form_pass_server_validation(self):
        import re
        js = self.client.get("/static/js/feedback.js").get_data(as_text=True)
        faculty = re.findall(r'id: "(F\d+)"', js)
        courses = re.findall(r'id: "(C\d+)"', js)
        self.assertTrue(faculty and courses)
        for f in faculty:
            for c in courses:
                self.assertEqual(self.post(valid_payload(faculty_id=f, course_id=c)).status_code, 201)


class TestCors(BackendTestCase):
    def test_allowed_origin_gets_header_and_unknown_does_not(self):
        ok = self.client.get("/api/health", headers={"Origin": "http://127.0.0.1:5500"})
        self.assertEqual(ok.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:5500")
        other = self.client.get("/api/health", headers={"Origin": "http://evil.example"})
        self.assertIsNone(other.headers.get("Access-Control-Allow-Origin"))

    def test_preflight(self):
        response = self.client.options("/api/feedback", headers={
            "Origin": "http://localhost:5500", "Access-Control-Request-Method": "POST"})
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:5500")


if __name__ == "__main__":
    unittest.main()
