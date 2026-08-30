import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


def get_db():
    """
    Opens a connection to the SQLite database.

    Returns:
        sqlite3.Connection: Database connection with row_factory and foreign keys enabled
    """
    conn = sqlite3.connect('spendly.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    """
    Creates database tables if they don't exist.
    Safe to call multiple times.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()


def seed_db():
    """
    Inserts demo user and sample expenses for development.
    Idempotent - checks for existing data before inserting.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Check if demo user already exists
    cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', ('demo@spendly.com',))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Insert demo user
    password_hash = generate_password_hash('demo123')
    cursor.execute(
        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
        ('Demo User', 'demo@spendly.com', password_hash)
    )
    demo_user_id = cursor.lastrowid

    # Insert 8 sample expenses
    sample_expenses = [
        (demo_user_id, 45.50, 'Food', '2026-08-05', 'Grocery shopping at Whole Foods'),
        (demo_user_id, 12.00, 'Transport', '2026-08-08', 'Uber ride to office'),
        (demo_user_id, 85.30, 'Bills', '2026-08-10', 'Electricity bill'),
        (demo_user_id, 120.00, 'Health', '2026-08-12', 'Doctor appointment'),
        (demo_user_id, 35.00, 'Entertainment', '2026-08-15', 'Movie tickets'),
        (demo_user_id, 67.80, 'Shopping', '2026-08-18', 'New running shoes'),
        (demo_user_id, 25.50, 'Other', '2026-08-20', 'Birthday gift'),
        (demo_user_id, 18.75, 'Food', '2026-08-22', 'Lunch at cafe'),
    ]

    cursor.executemany(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        sample_expenses
    )

    conn.commit()
    conn.close()


def get_user_by_email(email):
    """Return the user row for email, or None if not found."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return user


def create_user(name, email, password_hash):
    """Insert a user and return the new row id. Does not hash the password."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
        (name, email, password_hash)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def verify_password(password_hash, password):
    """Verify a plaintext password against a stored hash."""
    return check_password_hash(password_hash, password)

