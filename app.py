import os
import sqlite3
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secret_library_key_12345'
DATABASE = 'database.db'

def get_db_connection():
    """Establishes connection to the SQLite database with Row factory enabled."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")  # Enforce foreign key constraints
    return conn

def init_db():
    """Initializes the database, creates all necessary tables, and seeds sample data if empty."""
    db_exists = os.path.exists(DATABASE)
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            role TEXT NOT NULL DEFAULT 'Admin'
        )
    ''')

    # 2. Create books table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            isbn TEXT UNIQUE NOT NULL,
            publisher TEXT,
            quantity INTEGER NOT NULL DEFAULT 1,
            available INTEGER NOT NULL DEFAULT 1
        )
    ''')

    # 3. Create members table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT
        )
    ''')

    # 4. Create issued_books table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issued_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT NOT NULL DEFAULT 'Issued',
            FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE,
            FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()

    # Seed Default Admin Account if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        hashed_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, password, full_name, email, phone, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', hashed_password, 'Library Administrator', 'admin@library.com', '+1 555-0100', 'Admin'))
        conn.commit()

    conn.close()

# Initialize Database on load
init_db()

# --- Middleware/Decorators ---
def login_required(f):
    """Decorator to enforce authentication on routes."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    """Index redirect to dashboard or login page."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles admin authentication, setting session data on success."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Both fields are required.', 'error')
            return render_template('login.html')

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash('Successfully signed in.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.clear()
    flash('Successfully logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Renders dashboard dashboard with metrics, chart inputs, and recent transaction log."""
    conn = get_db_connection()

    # Aggregate metric cards statistics
    total_books_row = conn.execute('SELECT SUM(quantity) FROM books').fetchone()
    total_books = total_books_row[0] if total_books_row[0] is not None else 0

    available_books_row = conn.execute('SELECT SUM(available) FROM books').fetchone()
    available_books = available_books_row[0] if available_books_row[0] is not None else 0

    issued_books = conn.execute("SELECT COUNT(*) FROM issued_books WHERE status = 'Issued'").fetchone()[0]
    returned_books = conn.execute("SELECT COUNT(*) FROM issued_books WHERE status = 'Returned'").fetchone()[0]
    total_members = conn.execute('SELECT COUNT(*) FROM members').fetchone()[0]

    stats = {
        'total_books': total_books,
        'available_books': available_books,
        'issued_books': issued_books,
        'returned_books': returned_books,
        'total_members': total_members
    }

    # Fetch recent transactions
    transactions_query = '''
        SELECT ib.id, m.name AS member_name, m.phone AS member_phone, 
               b.title AS book_title, b.isbn, ib.issue_date, ib.due_date, ib.return_date, ib.status
        FROM issued_books ib
        JOIN members m ON ib.member_id = m.id
        JOIN books b ON ib.book_id = b.id
        ORDER BY ib.id DESC LIMIT 5
    '''
    transactions = conn.execute(transactions_query).fetchall()
    conn.close()

    return render_template('dashboard.html', stats=stats, transactions=transactions)

@app.route('/books', methods=['GET'])
@login_required
def books():
    """Renders page listing book list, offering search, filtering, and CRUD operations."""
    search_query = request.args.get('search', '').strip()
    selected_author = request.args.get('author', '').strip()
    selected_category = request.args.get('category', '').strip()

    conn = get_db_connection()

    # Fetch lookup lists for search filters
    authors = [row['author'] for row in conn.execute('SELECT DISTINCT author FROM books ORDER BY author').fetchall()]
    categories = [row['category'] for row in conn.execute('SELECT DISTINCT category FROM books ORDER BY category').fetchall()]

    # Build SQL dynamically based on filters
    query = 'SELECT * FROM books WHERE 1=1'
    params = []

    if search_query:
        query += ' AND (title LIKE ? OR isbn LIKE ? OR publisher LIKE ? OR author LIKE ?)'
        like_param = f'%{search_query}%'
        params.extend([like_param, like_param, like_param, like_param])

    if selected_author:
        query += ' AND author = ?'
        params.append(selected_author)

    if selected_category:
        query += ' AND category = ?'
        params.append(selected_category)

    query += ' ORDER BY id DESC'
    books_list = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('books.html', books=books_list, authors=authors, categories=categories,
                           search_query=search_query, selected_author=selected_author, selected_category=selected_category)

@app.route('/add-book', methods=['GET', 'POST'])
@login_required
def add_book():
    """Adds a new book to the database catalog."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        category = request.form.get('category', '').strip()
        isbn = request.form.get('isbn', '').strip()
        publisher = request.form.get('publisher', '').strip()
        quantity = request.form.get('quantity', '1')

        try:
            qty = int(quantity)
            if qty < 1:
                raise ValueError
        except ValueError:
            flash('Quantity must be an integer of 1 or more.', 'error')
            return render_template('add_book.html')

        if not title or not author or not category or not isbn:
            flash('Please fill in all required fields.', 'error')
            return render_template('add_book.html')

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Insert book. Available copies will match total quantity initially
            cursor.execute('''
                INSERT INTO books (title, author, category, isbn, publisher, quantity, available)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, author, category, isbn, publisher, qty, qty))
            conn.commit()
            flash(f"Book '{title}' successfully added to the catalog.", 'success')
            return redirect(url_for('books'))
        except sqlite3.IntegrityError:
            flash('A book with this ISBN already exists.', 'error')
        finally:
            conn.close()

    return render_template('add_book.html')

@app.route('/edit-book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    """Modifies details and total stock of a book, dynamically updating available quantities."""
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if not book:
        conn.close()
        flash('Book not found.', 'error')
        return redirect(url_for('books'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        category = request.form.get('category', '').strip()
        isbn = request.form.get('isbn', '').strip()
        publisher = request.form.get('publisher', '').strip()
        quantity_str = request.form.get('quantity', '1')

        try:
            new_qty = int(quantity_str)
            if new_qty < 1:
                raise ValueError
        except ValueError:
            flash('Quantity must be an integer of 1 or more.', 'error')
            conn.close()
            return render_template('edit_book.html', book=book)

        if not title or not author or not category or not isbn:
            flash('Please fill in all required fields.', 'error')
            conn.close()
            return render_template('edit_book.html', book=book)

        # Count active loans to verify the quantity adjustment
        active_loans = conn.execute(
            "SELECT COUNT(*) FROM issued_books WHERE book_id = ? AND status = 'Issued'",
            (book_id,)
        ).fetchone()[0]

        if new_qty < active_loans:
            flash(f"Cannot lower stock to {new_qty}. There are currently {active_loans} active loans of this book.", 'error')
            conn.close()
            return render_template('edit_book.html', book=book)

        # Calculate new availability: available = new_quantity - active_loans
        new_avail = new_qty - active_loans

        try:
            conn.execute('''
                UPDATE books
                SET title = ?, author = ?, category = ?, isbn = ?, publisher = ?, quantity = ?, available = ?
                WHERE id = ?
            ''', (title, author, category, isbn, publisher, new_qty, new_avail, book_id))
            conn.commit()
            flash(f"Book details for '{title}' updated successfully.", 'success')
            return redirect(url_for('books'))
        except sqlite3.IntegrityError:
            flash('Another book with this ISBN already exists.', 'error')
        finally:
            conn.close()

    conn.close()
    return render_template('edit_book.html', book=book)

@app.route('/delete-book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    """Deletes a book from catalog. Refuses delete if copies are currently checked out."""
    conn = get_db_connection()
    # Check if there are active loans
    active_loans = conn.execute(
        "SELECT COUNT(*) FROM issued_books WHERE book_id = ? AND status = 'Issued'",
        (book_id,)
    ).fetchone()[0]

    if active_loans > 0:
        flash(f"Cannot delete book. There are currently {active_loans} copies on active loans.", 'error')
        conn.close()
        return redirect(url_for('books'))

    # Proceed to delete book. Cascading deletes transactions.
    conn.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()
    flash('Book deleted from catalog successfully.', 'success')
    return redirect(url_for('books'))

@app.route('/issue-book', methods=['GET', 'POST'])
@login_required
def issue_book():
    """Handles issuing books to library members. Dynamically decrements stock availability."""
    preselected_book_id = request.args.get('book_id', '')

    conn = get_db_connection()
    available_books = conn.execute('SELECT * FROM books WHERE available > 0 ORDER BY title').fetchall()
    members = conn.execute('SELECT * FROM members ORDER BY name').fetchall()

    if request.method == 'POST':
        book_id = request.form.get('book_id')
        member_id = request.form.get('member_id')
        issue_date = request.form.get('issue_date')
        due_date = request.form.get('due_date')

        if not book_id or not member_id or not issue_date or not due_date:
            flash('All form fields are required.', 'error')
            conn.close()
            return redirect(url_for('issue_book', book_id=book_id))

        # Re-fetch book to check availability
        book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        if not book or book['available'] < 1:
            flash('Sorry, the selected book is currently not in stock.', 'error')
            conn.close()
            return redirect(url_for('issue_book'))

        # Insert Transaction
        conn.execute('''
            INSERT INTO issued_books (member_id, book_id, issue_date, due_date, status)
            VALUES (?, ?, ?, ?, 'Issued')
        ''', (member_id, book_id, issue_date, due_date))

        # Decrement Available Quantity
        conn.execute('UPDATE books SET available = available - 1 WHERE id = ?', (book_id,))
        conn.commit()
        conn.close()

        flash('Book successfully issued.', 'success')
        return redirect(url_for('dashboard'))

    conn.close()
    today_date = date.today().strftime('%Y-%m-%d')
    return render_template('issue_book.html', available_books=available_books, members=members,
                           preselected_book_id=preselected_book_id, today_date=today_date)

@app.route('/return-book', methods=['GET'])
@login_required
def return_books():
    """Renders return page displaying active loans and past history logs."""
    conn = get_db_connection()

    # Active borrows
    active_query = '''
        SELECT ib.id, ib.member_id, ib.book_id, ib.issue_date, ib.due_date,
               m.name AS member_name, m.phone AS member_phone,
               b.title AS book_title, b.author AS book_author, b.isbn
        FROM issued_books ib
        JOIN members m ON ib.member_id = m.id
        JOIN books b ON ib.book_id = b.id
        WHERE ib.status = 'Issued'
        ORDER BY ib.id ASC
    '''
    raw_loans = conn.execute(active_query).fetchall()

    # Process loans to calculate late fines
    active_loans = []
    today = date.today()
    for row in raw_loans:
        loan = dict(row)
        due_date_obj = datetime.strptime(loan['due_date'], '%Y-%m-%d').date()
        
        # Calculate days overdue and fine (Rate: $1.00 per day)
        if today > due_date_obj:
            loan['days_overdue'] = (today - due_date_obj).days
            loan['fine'] = loan['days_overdue'] * 1.00
        else:
            loan['days_overdue'] = 0
            loan['fine'] = 0.00
        
        active_loans.append(loan)

    # Returned borrows history
    returned_query = '''
        SELECT ib.id, m.name AS member_name, m.phone AS member_phone,
               b.title AS book_title, b.isbn, ib.issue_date, ib.due_date, ib.return_date
        FROM issued_books ib
        JOIN members m ON ib.member_id = m.id
        JOIN books b ON ib.book_id = b.id
        WHERE ib.status = 'Returned'
        ORDER BY ib.return_date DESC LIMIT 10
    '''
    returned_loans = conn.execute(returned_query).fetchall()
    conn.close()

    return render_template('return_book.html', active_loans=active_loans, returned_loans=returned_loans)

@app.route('/return-book-action/<int:loan_id>', methods=['POST'])
@login_required
def return_book_action(loan_id):
    """Processes return transactions. Restores book copy to stock availability."""
    conn = get_db_connection()
    loan = conn.execute('SELECT * FROM issued_books WHERE id = ?', (loan_id,)).fetchone()

    if not loan or loan['status'] != 'Issued':
        conn.close()
        flash('Invalid transaction or book already returned.', 'error')
        return redirect(url_for('return_books'))

    today_date = date.today().strftime('%Y-%m-%d')

    # Update loan transaction
    conn.execute('''
        UPDATE issued_books
        SET return_date = ?, status = 'Returned'
        WHERE id = ?
    ''', (today_date, loan_id))

    # Increment available copies back
    conn.execute('UPDATE books SET available = available + 1 WHERE id = ?', (loan['book_id'],))
    conn.commit()
    conn.close()

    flash('Book successfully checked in and returned to stock.', 'success')
    return redirect(url_for('return_books'))

# --- Member Management ---

@app.route('/members', methods=['GET'])
@login_required
def members():
    """Lists registered library members, with search capabilities."""
    search_query = request.args.get('search', '').strip()
    conn = get_db_connection()

    query = '''
        SELECT m.*, 
               (SELECT COUNT(*) FROM issued_books WHERE member_id = m.id AND status = 'Issued') AS active_loans
        FROM members m
        WHERE 1=1
    '''
    params = []
    if search_query:
        query += ' AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)'
        like_param = f'%{search_query}%'
        params.extend([like_param, like_param, like_param])

    query += ' ORDER BY m.id DESC'
    members_list = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('members.html', members=members_list, search_query=search_query)

@app.route('/add-member', methods=['GET', 'POST'])
@login_required
def add_member():
    """Registers a new library member."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        if not name or not email or not phone:
            flash('All details are required to register a member.', 'error')
            return render_template('add_member.html')

        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO members (name, email, phone)
                VALUES (?, ?, ?)
            ''', (name, email, phone))
            conn.commit()
            flash(f"Member '{name}' registered successfully.", 'success')
            return redirect(url_for('members'))
        except sqlite3.IntegrityError:
            flash('A member with this email already exists.', 'error')
        finally:
            conn.close()

    return render_template('add_member.html')

@app.route('/delete-member/<int:member_id>', methods=['POST'])
@login_required
def delete_member(member_id):
    """Deletes a member record if they have no active loans."""
    conn = get_db_connection()
    # Check for active loans
    active_loans = conn.execute(
        "SELECT COUNT(*) FROM issued_books WHERE member_id = ? AND status = 'Issued'",
        (member_id,)
    ).fetchone()[0]

    if active_loans > 0:
        flash('Cannot delete member. They have active books borrowed.', 'error')
        conn.close()
        return redirect(url_for('members'))

    # Proceed to delete member
    conn.execute('DELETE FROM members WHERE id = ?', (member_id,))
    conn.commit()
    conn.close()

    flash('Member record deleted successfully.', 'success')
    return redirect(url_for('members'))

# --- Profile Endpoints ---

@app.route('/profile')
@login_required
def profile():
    """Renders profile panel for admin settings."""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/profile/edit', methods=['POST'])
@login_required
def profile_edit():
    """Updates non-sensitive details of the currently logged-in user profile."""
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()

    if not full_name:
        flash('Full name is required.', 'error')
        return redirect(url_for('profile'))

    conn = get_db_connection()
    conn.execute('''
        UPDATE users
        SET full_name = ?, email = ?, phone = ?
        WHERE id = ?
    ''', (full_name, email, phone, session['user_id']))
    conn.commit()
    conn.close()

    session['full_name'] = full_name  # Update session cache
    flash('Profile details updated successfully.', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Updates password securely after verifying current password."""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not current_password or not new_password or not confirm_password:
        flash('Please fill in all password fields.', 'error')
        return redirect(url_for('profile'))

    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('profile'))

    if len(new_password) < 4:
        flash('New password must be at least 4 characters long.', 'error')
        return redirect(url_for('profile'))

    conn = get_db_connection()
    user = conn.execute('SELECT password FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if not check_password_hash(user['password'], current_password):
        flash('Incorrect current password.', 'error')
        conn.close()
        return redirect(url_for('profile'))

    # Update password securely
    hashed_pwd = generate_password_hash(new_password)
    conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_pwd, session['user_id']))
    conn.commit()
    conn.close()

    flash('Password changed successfully.', 'success')
    return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
