from datetime import datetime
from database.db import get_db


def get_user_by_id(user_id):
    """
    Fetch user info and format for profile display.

    Args:
        user_id: Integer user ID

    Returns:
        dict with keys: name, email, initials, member_since
        None if user not found
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, created_at FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    # Parse created_at and format as "Month YYYY"
    created_at = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
    member_since = created_at.strftime('%B %Y')

    # Extract initials
    name_parts = row['name'].strip().split()
    if len(name_parts) >= 2:
        initials = name_parts[0][0].upper() + name_parts[-1][0].upper()
    else:
        initials = row['name'][:2].upper() if len(row['name']) >= 2 else row['name'].upper()

    return {
        'name': row['name'],
        'email': row['email'],
        'initials': initials,
        'member_since': member_since
    }


def get_category_breakdown(user_id, date_from=None, date_to=None):
    """
    Calculate category spending breakdown with percentages.

    Args:
        user_id: Integer user ID
        date_from: Optional ISO date string (YYYY-MM-DD) for range start
        date_to: Optional ISO date string (YYYY-MM-DD) for range end

    Returns:
        List of dicts with keys: name, total (float), percentage (int)
        Ordered by total DESC. Empty list if no expenses.
        Percentages guaranteed to sum to exactly 100.
    """
    conn = get_db()
    cursor = conn.cursor()

    if date_from and date_to:
        cursor.execute('''
            SELECT
                category,
                SUM(amount) as total
            FROM expenses
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id, date_from, date_to))
    else:
        cursor.execute('''
            SELECT
                category,
                SUM(amount) as total
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    # Calculate grand total
    grand_total = sum(row['total'] for row in rows)

    # Calculate raw percentages and round
    categories = []
    for row in rows:
        raw_percentage = (row['total'] / grand_total) * 100
        rounded_percentage = round(raw_percentage)
        categories.append({
            'name': row['category'],
            'total': row['total'],
            'percentage': rounded_percentage
        })

    # Adjust rounding to ensure sum is exactly 100
    percentage_sum = sum(cat['percentage'] for cat in categories)
    if percentage_sum != 100 and categories:
        difference = 100 - percentage_sum
        categories[0]['percentage'] += difference

    return categories


def get_summary_stats(user_id, date_from=None, date_to=None):
    """
    Calculate summary statistics for a user's expenses.

    Args:
        user_id: Integer user ID
        date_from: Optional ISO date string (YYYY-MM-DD) for range start
        date_to: Optional ISO date string (YYYY-MM-DD) for range end

    Returns:
        dict with keys: total_spent (float), transaction_count (int), top_category (string)
    """
    conn = get_db()
    cursor = conn.cursor()

    # Query 1: Get total spent and transaction count
    if date_from and date_to:
        cursor.execute('''
            SELECT
                COALESCE(SUM(amount), 0) as total_spent,
                COUNT(*) as transaction_count
            FROM expenses
            WHERE user_id = ? AND date BETWEEN ? AND ?
        ''', (user_id, date_from, date_to))
    else:
        cursor.execute('''
            SELECT
                COALESCE(SUM(amount), 0) as total_spent,
                COUNT(*) as transaction_count
            FROM expenses
            WHERE user_id = ?
        ''', (user_id,))
    row = cursor.fetchone()
    total_spent = float(row['total_spent'])
    transaction_count = int(row['transaction_count'])

    # Query 2: Get top category
    if date_from and date_to:
        cursor.execute('''
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY category
            ORDER BY total DESC
            LIMIT 1
        ''', (user_id, date_from, date_to))
    else:
        cursor.execute('''
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY total DESC
            LIMIT 1
        ''', (user_id,))
    category_row = cursor.fetchone()
    conn.close()

    # If no expenses, return default values
    if category_row is None:
        top_category = "—"
    else:
        top_category = category_row['category']

    return {
        'total_spent': total_spent,
        'transaction_count': transaction_count,
        'top_category': top_category
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """
    Fetch recent expenses for a user.

    Args:
        user_id: Integer user ID
        limit: Maximum number of transactions to return (default 10)
        date_from: Optional ISO date string (YYYY-MM-DD) for range start
        date_to: Optional ISO date string (YYYY-MM-DD) for range end

    Returns:
        List of dicts with keys: date, description, category, amount
        Empty list if no expenses found
    """
    conn = get_db()
    cursor = conn.cursor()

    if date_from and date_to:
        cursor.execute(
            'SELECT date, description, category, amount '
            'FROM expenses '
            'WHERE user_id = ? AND date BETWEEN ? AND ? '
            'ORDER BY date DESC, created_at DESC '
            'LIMIT ?',
            (user_id, date_from, date_to, limit)
        )
    else:
        cursor.execute(
            'SELECT date, description, category, amount '
            'FROM expenses '
            'WHERE user_id = ? '
            'ORDER BY date DESC, created_at DESC '
            'LIMIT ?',
            (user_id, limit)
        )
    rows = cursor.fetchall()
    conn.close()

    # Convert Row objects to dicts
    return [dict(row) for row in rows]


def insert_expense(user_id, amount, category, date, description=None):
    """
    Insert a new expense record for a user.

    Args:
        user_id: Integer user ID
        amount: Float amount of the expense (must be > 0)
        category: String category name (must be one of the fixed 7 options)
        date: ISO date string (YYYY-MM-DD)
        description: Optional string description, or None if blank

    Returns:
        The row id of the newly inserted expense

    Note: Caller must ensure user_id matches the authenticated user.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        (user_id, amount, category, date, description)
    )
    conn.commit()
    expense_id = cursor.lastrowid
    conn.close()
    return expense_id
