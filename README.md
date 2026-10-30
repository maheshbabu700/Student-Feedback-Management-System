# College Student Feedback System - Part 1: Feedback Form (Frontend)

## Project overview
A responsive student feedback form built with HTML, CSS and vanilla JavaScript.
Students enter their details, choose a faculty member and course, give a 1-5 star
rating, write comments and submit. This is **Part 1 of 3** (frontend only).
The backend (Flask + SQLite) and the admin dashboard come in later parts.

## Features implemented
- Student name and student ID / roll number fields
- Faculty and course dropdowns with sample data (easy to edit)
- Interactive 5-star rating: Poor, Fair, Good, Very Good, Excellent
- Mouse hover preview, click, and keyboard support (Tab + arrow keys)
- Comments text area (whitespace-only comments are rejected)
- Validation of all fields with clear error messages
- Frontend-only success message
- Blue-and-white responsive design (mobile, tablet, desktop)
- Form field names ready for the backend: `student_name`, `student_id`,
  `faculty_id`, `course_id`, `rating`, `comments`

## Folder structure
```
01_Student_Feedback_System/
|-- templates/
|   `-- feedback.html
|-- static/
|   |-- css/
|   |   `-- style.css
|   `-- js/
|       `-- feedback.js
`-- README.md
```

## How to open and test the form
**Option A: VS Code Live Server (recommended)**
1. Open the `01_Student_Feedback_System` folder in VS Code (File > Open Folder).
2. Install the "Live Server" extension (Extensions icon on the left, search, Install).
3. Right-click `templates/feedback.html` and choose "Open with Live Server".

**Option B: Open the file directly**
1. In File Explorer, open `01_Student_Feedback_System\templates`.
2. Double-click `feedback.html`. It opens in your default browser.

The CSS and JS are linked with relative paths (`../static/...`), so no Flask is needed.

## How to test validation
Open the browser console with F12 to check for errors (there should be none).
1. Click "Submit feedback" with everything empty: every field shows an error.
2. Fill only name and ID: faculty, course, rating and comments errors remain.
3. Leave the rating empty with all else filled: the rating error appears.
4. Type only spaces in comments: the comments error appears.
5. Fill everything correctly: a green success message appears.
6. Press F12 > Console after a valid submit to see the organised data object.
7. Rating by keyboard: press Tab to reach the stars, then use the Left/Right arrow keys.
8. Responsive check: press Ctrl+Shift+M in the browser dev tools and pick a phone size.

## Corrections in this version
- **Names in any language are accepted.** The old rule allowed only A-Z, so names such as "Śrinivas Rao" or names in Telugu/Hindi script were rejected. Student names may contain letters of any language (including accents, e.g. Śrinivas, or Telugu/Hindi script), spaces, dots, hyphens and apostrophes. Digits and symbols are rejected, both in the form and on the server.
- The star rating container is now positioned, so focusing a star can never make the page jump.
- Success/failure messages are built as plain text (no `innerHTML`).
- A `<noscript>` message tells the user that JavaScript is required.
- Added `.gitignore`.

## Important note
**This frontend does not save data permanently.** Submitting only validates the form
and shows a message. Nothing is sent to a server or stored in a database. Refreshing
the page clears everything.

## Connecting the backend later
1. Flask serves `templates/feedback.html` from a route, and `static/` is served automatically.
2. In the HTML, change the links to Flask style, for example
   `href="{{ url_for('static', filename='css/style.css') }}"`.
3. Add `method="POST" action="/submit-feedback"` to the form, or use `fetch()` in
   `feedback.js` to send the object built in `validateForm()`.
4. The field names already match the planned database columns.
5. Replace `FACULTY_LIST` and `COURSE_LIST` in `feedback.js` with data loaded from the database.
6. Always validate again on the server; browser validation alone is not secure.
