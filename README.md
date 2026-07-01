# Library Management System

A complete, production-quality, responsive Library Management System built using Python Flask, SQLite, HTML5, CSS3, Bootstrap 5, and JavaScript.

This application features a modern, dashboard layout tailored for library administrators to manage books, track members, and register borrow-and-return transactions with automated stock updates and late fine computations.

---

## Folder Structure

```text
LibraryManagementSystem/
├── app.py                  # Core Flask backend server and SQLite schema initialization
├── database.db             # SQLite database file (created automatically on startup)
├── requirements.txt        # Backend dependencies
├── README.md               # Setup and usage guide
├── static/
│   ├── css/
│   │   └── style.css       # Custom styles, transitions, variables, and layouts
│   ├── js/
│   │   └── script.js       # Password toggles, dynamic date offsets, and confirm popups
│   └── images/
│       └── logo.png        # System brand logo
└── templates/
    ├── layout.html         # Master layout with responsive sidebar and topbar
    ├── login.html          # Portal sign-in form with password visibility toggle
    ├── dashboard.html      # Stats summary counters, doughnut charts, and recent actions
    ├── books.html          # Book catalog listing with multi-field search and filters
    ├── add_book.html       # Book addition form
    ├── edit_book.html      # Book metadata edit panel
    ├── members.html        # Member register listing and filters
    ├── add_member.html     # Member registration form
    ├── issue_book.html     # Borrow transaction logger
    ├── return_book.html    # Active borrow list, fine calculator, and return check-in
    └── profile.html        # Admin settings, details manager, and password changer
```

---

## Core Features

1. **Authentication**: Session-based login/logout, password visibility toggle, secure bcrypt hashing of passwords (`werkzeug.security`).
2. **Dashboard Overview**: Metrics counters, live inventory doughnut chart using Chart.js, quick-action navigation, and recent transactional log feed.
3. **Book Catalog (CRUD)**:
   - Dynamic searches and filters by Category and Author.
   - Stock controller (prevents lowering stock below checked-out quantity).
   - Interactive inventory badges (Available vs. Out of stock).
4. **Member Management**:
   - Register member details (Full Name, Unique Email, Phone).
   - View list and search dynamically.
   - Safety checks (prevents deleting members with active checked-out loans).
5. **Issue Book Transaction**:
   - Limit books selection only to those currently in stock.
   - Dynamic due-date calculations (adds 14 days automatically).
   - Reduces stock quantity automatically.
6. **Return Book Module**:
   - Live view of current issued logs.
   - Calculates days overdue and late fines ($1.00/day fine) dynamically.
   - Updates stock count and check-in return timestamp on execution.
7. **Profile Configuration**: Edit full name, email, phone, and securely change account password.

---

## Installation & Launch Steps

Ensure you have Python 3.8+ installed on your system.

### 1. Extract and Open Project
Open the project directory in your terminal or Visual Studio Code:
```bash
cd LibraryManagementSystem
```

### 2. Set Up Virtual Environment (Optional but Recommended)
If a virtual environment `venv` is not already configured, create it:
```bash
python -m venv venv
```
Activate the environment:
* **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies
Run:
```bash
pip install -r requirements.txt
```

### 4. Start the Application
Launch the Flask development server:
```bash
python app.py
```
Upon startup, `app.py` will:
1. Detect that `database.db` does not exist or needs initialization.
2. Build the database structure.
3. Seed a default admin user and sample book catalog items.
4. Launch the server at `http://127.0.0.1:5000/`.

---

## Default Accounts

* **Admin Portal Login**:
  - **Username**: `admin`
  - **Password**: `admin123`

---

## Verification & Testing Instructions

1. **Verify Login**: Open `http://127.0.0.1:5000/` in your browser. Verify that visiting any page redirects you to `/login`. Sign in using `admin` / `admin123`.
2. **Verify Dashboard**: Check that cards (Total Books, Available Copies, Total Members, etc.) display correct numbers. Ensure the Chart.js doughnut chart loads.
3. **Verify Search & Filter**: Navigate to **Manage Books**. Type "Gatsby" or select a category and click "Filter" to verify search functionality.
4. **Verify Add Book**: Click **Add New Book**. Fill out the details, submit, and confirm that it shows up in the catalog.
5. **Verify Issue Book**: Go to **Issue Book**, pick a book and member, and click "Confirm Issue". Check that the book's available quantity decreases by 1 on the catalog.
6. **Verify Late Fine Calculation**: Check the **Return Book** panel. The sample transaction seeded for Bob Jones has a due date of `2026-06-15`, which calculates an active overdue late fine.
7. **Verify Return Action**: Click **Return Book** for Bob Jones' loan. Verify that the book is checked in (removed from active list, added to history) and that the available quantity on the catalog increases by 1.
8. **Verify Profile Modification**: Head to **My Profile**, edit details, and save. Check that your name updates instantly in the header. Try updating your password and verify you can login with the new credentials.
