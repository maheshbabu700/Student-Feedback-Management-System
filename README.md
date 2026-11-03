# College Student Feedback Management System

Integrated Flask + SQLite application containing the student feedback form, feedback API,
admin login, dashboard, feedback records and reports.

## Run the integrated application

1. Open this project folder in VS Code.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (optional but recommended):

   Windows:
   ```bat
   python -m venv .venv
   .venv\\Scripts\\activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Start Flask:
   ```bash
   python app.py
   ```

6. Open the student form at `http://127.0.0.1:5000/`.
   Submit feedback here. Do not open `templates/feedback.html` directly and do not
   use VS Code Live Server for submissions; the form must use the Flask server.

7. Log in at `http://127.0.0.1:5000/login` and open the dashboard.
   The development defaults are username `admin` and password `Admin@12345`.
   Change these before any real deployment by setting `ADMIN_USERNAME`,
   `ADMIN_PASSWORD`, and `SECRET_KEY` environment variables.

## Verify that submissions are saved

- Health check: `http://127.0.0.1:5000/api/health`
- Feedback API: `http://127.0.0.1:5000/api/feedback`
- SQLite database: `database/feedback.db`

The student form sends JSON to `POST /api/feedback`. The dashboard and reports read
from the same SQLite database. Refresh the dashboard after a submission to see updated
summary figures and charts.

## Run backend tests

```bash
python -m unittest discover -s tests -v
```

Tests use temporary databases and do not modify the project's real feedback database.
