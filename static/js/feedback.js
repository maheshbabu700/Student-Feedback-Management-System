// ============================================================
// College Student Feedback System - Part 1 (frontend only)
// No data is sent anywhere or saved. Validation + UI only.
// ============================================================

// ---- Easy-to-change data -----------------------------------
// Later, the backend can provide these lists from the database.
// "id" becomes the value sent as faculty_id / course_id.
const FACULTY_LIST = [
  { id: "F100", name: "Prof. Jeevan Kumar"},
  { id: "F101", name: "Dr. A. Sharma" },
  { id: "F102", name: "Prof. B. Reddy" },
  { id: "F103", name: "Dr. C. Nair" },
  { id: "F104", name: "Prof. D. Iyer" },
  { id: "F105", name: "Dr. E. Gupta" },
  { id: "F106", name: "Prof. F. Mehta" },
  { id: "F107", name: "Dr. G. Rao" },
  { id: "F108", name: "Prof. H. Singh" },
  { id: "F109", name: "Dr. I. Verma" }
];

const COURSE_LIST = [
  { id: "C200", name: "Full Stack Development"},
  { id: "C201", name: "Python Programming" },
  { id: "C202", name: "Java Programming" },
  { id: "C203", name: "Database Management Systems (DBMS)" },
  { id: "C204", name: "Data Structures" },
  { id: "C205", name: "Algorithms" },
  { id: "C206", name: "Operating Systems" },
  { id: "C207", name: "Computer Networks" },
  { id: "C208", name: "Software Engineering" },
  { id: "C209", name: "Artificial Intelligence" }
];

// Star labels: index 0 = 1 star
const RATING_LABELS = ["Poor", "Fair", "Good", "Very Good", "Excellent"];

// ---- Page elements -----------------------------------------
const form = document.getElementById("feedbackForm");
const studentNameInput = document.getElementById("student_name");
const studentIdInput = document.getElementById("student_id");
const facultySelect = document.getElementById("faculty_id");
const courseSelect = document.getElementById("course_id");
const commentsInput = document.getElementById("comments");
const ratingInput = document.getElementById("rating");     // hidden field holding the rating
const starsContainer = document.getElementById("stars");
const ratingText = document.getElementById("ratingText");
const formStatus = document.getElementById("formStatus");

// ---- Fill dropdowns ----------------------------------------
function fillDropdown(selectElement, items, placeholder) {
  selectElement.innerHTML = "";
  const first = document.createElement("option");
  first.value = "";
  first.textContent = placeholder;
  selectElement.appendChild(first);

  items.forEach(function (item) {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.name;
    selectElement.appendChild(option);
  });
}

fillDropdown(facultySelect, FACULTY_LIST, "Select faculty");
fillDropdown(courseSelect, COURSE_LIST, "Select course");

// ---- Build star rating -------------------------------------
// Each star is a radio button + label, so arrow keys / Tab / Space work natively.
RATING_LABELS.forEach(function (label, index) {
  const value = index + 1;

  const radio = document.createElement("input");
  radio.type = "radio";
  radio.name = "star_rating";
  radio.id = "star" + value;
  radio.value = value;

  const starLabel = document.createElement("label");
  starLabel.htmlFor = radio.id;
  starLabel.textContent = "\u2605";                       // star character
  starLabel.title = value + " - " + label;
  starLabel.setAttribute("aria-label", value + (value === 1 ? " star" : " stars") + ", " + label);

  starsContainer.appendChild(radio);
  starsContainer.appendChild(starLabel);

  radio.addEventListener("change", function () {
    setRating(value);
  });

  // Hover preview with mouse
  starLabel.addEventListener("mouseenter", function () { highlightStars(value); });
});

starsContainer.addEventListener("mouseleave", function () {
  highlightStars(Number(ratingInput.value) || 0);       // go back to selected rating
});

// Colour the first "count" stars
function highlightStars(count) {
  const labels = starsContainer.querySelectorAll("label");
  labels.forEach(function (lbl, i) {
    lbl.classList.toggle("filled", i < count);
  });
}

// Save the chosen rating so JavaScript (and later the backend) can read it
function setRating(value) {
  ratingInput.value = value;
  highlightStars(value);
  ratingText.textContent = value + " of 5 - " + RATING_LABELS[value - 1];
  ratingText.classList.add("chosen");
  clearError("rating");
}

function resetRating() {
  ratingInput.value = "";
  highlightStars(0);
  ratingText.textContent = "No rating selected";
  ratingText.classList.remove("chosen");
  starsContainer.querySelectorAll("input").forEach(function (r) { r.checked = false; });
}

// ---- Error helpers -----------------------------------------
function showError(fieldName, message) {
  document.getElementById(fieldName + "_error").textContent = message;
  const field = document.getElementById(fieldName);
  if (field && field.type !== "hidden") {
    field.classList.add("invalid");
    field.setAttribute("aria-invalid", "true");
  }
}

function clearError(fieldName) {
  document.getElementById(fieldName + "_error").textContent = "";
  const field = document.getElementById(fieldName);
  if (field) {
    field.classList.remove("invalid");
    field.removeAttribute("aria-invalid");
  }
}

function clearAllErrors() {
  ["student_name", "student_id", "faculty_id", "course_id", "rating", "comments"].forEach(clearError);
  formStatus.textContent = "";
  formStatus.className = "status";
}

// ---- Validation --------------------------------------------
// Returns an object with the cleaned values, or null if something is wrong.
function validateForm() {
  let isValid = true;
  let firstInvalid = null;

  function fail(fieldName, message, focusTarget) {
    showError(fieldName, message);
    isValid = false;
    if (!firstInvalid) { firstInvalid = focusTarget; }
  }

  const studentName = studentNameInput.value.trim();
  const studentId = studentIdInput.value.trim();
  const facultyId = facultySelect.value;
  const courseId = courseSelect.value;
  const rating = ratingInput.value;
  const comments = commentsInput.value.trim();

  // Name: required, at least 2 characters, letters of any language (including accents and
  // combining marks, e.g. Telugu or Hindi), spaces, dots, hyphens and apostrophes.
  // The server (app.py, is_valid_name) applies the same rule.
  if (studentName === "") {
    fail("student_name", "Enter your name.", studentNameInput);
  } else if (studentName.length < 2 || !/^\p{L}[\p{L}\p{M} .'\u2019-]*$/u.test(studentName)) {
    fail("student_name", "Use letters only (spaces, dots, hyphens and apostrophes are allowed).", studentNameInput);
  }

  // Student ID: required, letters and numbers only, 4-20 characters
  if (studentId === "") {
    fail("student_id", "Enter your student ID or roll number.", studentIdInput);
  } else if (!/^[A-Za-z0-9-]{4,20}$/.test(studentId)) {
    fail("student_id", "Use 4 to 20 letters or numbers (no spaces).", studentIdInput);
  }

  if (facultyId === "") {
    fail("faculty_id", "Select a faculty member.", facultySelect);
  }

  if (courseId === "") {
    fail("course_id", "Select a course.", courseSelect);
  }

  if (rating === "") {
    fail("rating", "Choose a star rating from 1 to 5.", starsContainer.querySelector("input"));
  }

  if (comments === "") {
    fail("comments", "Write your comments. Spaces alone are not accepted.", commentsInput);
  }

  if (!isValid) {
    firstInvalid.focus();   // move the cursor to the first problem
    return null;
  }

  // Field names match the planned Flask/SQLite columns
  return {
    student_name: studentName,
    student_id: studentId,
    faculty_id: facultyId,
    course_id: courseId,
    rating: Number(rating),
    comments: comments
  };
}

// ---- Events ------------------------------------------------
form.addEventListener("submit", async function (event) {
  event.preventDefault();
  clearAllErrors();

  const feedbackData = validateForm();

  if (feedbackData === null) {
    formStatus.textContent = "Please fix the highlighted fields and submit again.";
    formStatus.className = "status fail";
    return;
  }

  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  submitButton.textContent = "Submitting...";
  formStatus.textContent = "Saving your feedback...";
  formStatus.className = "status";

  try {
    // Send the validated form data to the Flask API. This page must be
    // opened through the Flask server (http://127.0.0.1:5000/).
    const response = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(feedbackData)
    });

    const result = await response.json().catch(function () { return {}; });

    if (!response.ok || !result.success) {
      if (result.errors) {
        Object.keys(result.errors).forEach(function (field) {
          showError(field, result.errors[field]);
        });
      }
      throw new Error(result.message || "Feedback could not be saved. Please try again.");
    }

    formStatus.textContent = "Feedback submitted and saved successfully. Thank you!";
    formStatus.className = "status success";
    form.reset();
    resetRating();
  } catch (error) {
    formStatus.textContent = error.message ||
      "Could not connect to the server. Open the form through the Flask application and try again.";
    formStatus.className = "status fail";
    console.error("Feedback submission failed:", error);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Submit feedback";
    formStatus.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
});

// Clear a field's error as soon as the user fixes it
[
  ["student_name", studentNameInput],
  ["student_id", studentIdInput],
  ["faculty_id", facultySelect],
  ["course_id", courseSelect],
  ["comments", commentsInput]
].forEach(function (pair) {
  const eventName = pair[1].tagName === "SELECT" ? "change" : "input";
  pair[1].addEventListener(eventName, function () { clearError(pair[0]); });
});
