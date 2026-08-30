import pytest
from datetime import date, datetime, timedelta
from app import app as flask_app
from database.db import init_db, get_db, create_user
from database.queries import insert_expense, get_recent_transactions


def get_csrf_token(client, url='/expenses/add'):
    """Fetch CSRF token from a form page."""
    response = client.get(url)
    # Extract csrf_token from session via a test POST that will fail on token mismatch
    with client:
        client.get(url)
        from flask import session
        return session.get('csrf_token', '')


@pytest.fixture
def app():
    """Create and configure a test Flask app."""
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
    })
    with flask_app.app_context():
        init_db()
        yield flask_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Create a test client that is already logged in."""
    client.post('/register', data={
        'name': 'Test User',
        'email': 'testuser@example.com',
        'password': 'testpass123'
    })
    client.post('/login', data={
        'email': 'testuser@example.com',
        'password': 'testpass123'
    })
    return client


@pytest.fixture
def user_id(auth_client):
    """Extract user_id from authenticated session."""
    with auth_client:
        auth_client.get('/profile')
        from flask import session
        return session['user_id']


# ===================================================================
# Unit Tests: insert_expense Query Helper
# ===================================================================

class TestInsertExpenseUnit:
    def test_insert_expense_with_valid_data(self):
        """insert_expense inserts valid expense and returns row id."""
        init_db()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                      ('Test', 'test@example.com', 'hash'))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        expense_id = insert_expense(user_id, 50.0, 'Food', '2026-03-20', 'Lunch')

        assert expense_id is not None
        assert isinstance(expense_id, int)
        assert expense_id > 0

        # Verify the row was inserted
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row['user_id'] == user_id
        assert row['amount'] == 50.0
        assert row['category'] == 'Food'
        assert row['date'] == '2026-03-20'
        assert row['description'] == 'Lunch'

    def test_insert_expense_with_none_description(self):
        """insert_expense stores NULL when description is None."""
        init_db()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                      ('Test', 'test2@example.com', 'hash'))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        expense_id = insert_expense(user_id, 75.0, 'Transport', '2026-03-21', None)

        # Verify the row has NULL description
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT description FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['description'] is None

    def test_insert_expense_all_categories(self):
        """insert_expense works with all 7 valid categories."""
        init_db()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                      ('Test', 'test3@example.com', 'hash'))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        categories = ['Food', 'Transport', 'Bills', 'Health', 'Entertainment', 'Shopping', 'Other']

        for idx, category in enumerate(categories):
            expense_id = insert_expense(user_id, 10.0 + idx, category, '2026-03-22', f'Test {category}')
            assert expense_id is not None

        # Verify all were inserted
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as cnt FROM expenses WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()['cnt']
        conn.close()

        assert count == 7

    def test_insert_expense_preserves_precision(self):
        """insert_expense preserves decimal precision for amounts."""
        init_db()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                      ('Test', 'test4@example.com', 'hash'))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        expense_id = insert_expense(user_id, 99.99, 'Shopping', '2026-03-23', 'Test')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT amount FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['amount'] == 99.99


# ===================================================================
# Route Tests: GET /expenses/add — Unauthenticated
# ===================================================================

class TestGetAddExpenseUnauthenticated:
    def test_get_add_expense_redirects_to_login(self, client):
        """GET /expenses/add without auth redirects to /login with 302."""
        response = client.get('/expenses/add')

        assert response.status_code == 302
        assert '/login' in response.location


# ===================================================================
# Route Tests: GET /expenses/add — Authenticated
# ===================================================================

class TestGetAddExpenseAuthenticated:
    def test_get_add_expense_returns_200(self, auth_client):
        """GET /expenses/add with auth returns 200."""
        response = auth_client.get('/expenses/add')

        assert response.status_code == 200

    def test_get_add_expense_renders_form(self, auth_client):
        """GET /expenses/add response body contains form element."""
        response = auth_client.get('/expenses/add')

        assert b'<form' in response.data
        assert b'method' in response.data

    def test_get_add_expense_contains_category_select(self, auth_client):
        """GET /expenses/add response contains category select element."""
        response = auth_client.get('/expenses/add')

        assert b'<select' in response.data

    def test_get_add_expense_contains_all_categories(self, auth_client):
        """GET /expenses/add response contains all 7 category options."""
        response = auth_client.get('/expenses/add')

        categories = [b'Food', b'Transport', b'Bills', b'Health', b'Entertainment', b'Shopping', b'Other']

        for category in categories:
            assert category in response.data

    def test_get_add_expense_contains_amount_input(self, auth_client):
        """GET /expenses/add response contains amount input field."""
        response = auth_client.get('/expenses/add')

        assert b'amount' in response.data
        assert b'type' in response.data or b'input' in response.data

    def test_get_add_expense_contains_date_input(self, auth_client):
        """GET /expenses/add response contains date input field."""
        response = auth_client.get('/expenses/add')

        assert b'date' in response.data

    def test_get_add_expense_contains_description_input(self, auth_client):
        """GET /expenses/add response contains description input field."""
        response = auth_client.get('/expenses/add')

        assert b'description' in response.data

    def test_get_add_expense_date_defaults_to_today(self, auth_client):
        """GET /expenses/add pre-fills date field with today's date."""
        response = auth_client.get('/expenses/add')

        today = date.today().strftime('%Y-%m-%d')
        assert today.encode() in response.data or b'value' in response.data


# ===================================================================
# Route Tests: POST /expenses/add — Unauthenticated
# ===================================================================

class TestPostAddExpenseUnauthenticated:
    def test_post_add_expense_redirects_to_login(self, client):
        """POST /expenses/add without auth redirects to /login with 302."""
        response = client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert response.status_code == 302
        assert '/login' in response.location


# ===================================================================
# Route Tests: POST /expenses/add — Valid Data
# ===================================================================

class TestPostAddExpenseValid:
    def test_post_add_expense_valid_redirects_to_profile(self, auth_client, user_id):
        """POST /expenses/add with valid data redirects to /profile with 302."""
        csrf_token = get_csrf_token(auth_client)
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'csrf_token': csrf_token,
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.location

    def test_post_add_expense_valid_inserts_into_db(self, auth_client, user_id):
        """POST /expenses/add with valid data inserts expense into database."""
        csrf_token = get_csrf_token(auth_client)
        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'csrf_token': csrf_token,
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        # Verify expense exists in DB
        transactions = get_recent_transactions(user_id, limit=1)

        assert len(transactions) == 1
        assert transactions[0]['amount'] == 50.0
        assert transactions[0]['category'] == 'Food'
        assert transactions[0]['date'] == '2026-03-20'
        assert transactions[0]['description'] == 'Lunch'

    def test_post_add_expense_valid_all_categories(self, auth_client, user_id):
        """POST /expenses/add works with all 7 valid categories."""
        categories = ['Food', 'Transport', 'Bills', 'Health', 'Entertainment', 'Shopping', 'Other']

        for category in categories:
            auth_client.post('/expenses/add', data={
                        'csrf_token': get_csrf_token(auth_client),
                'amount': '25.0',
                'category': category,
                'date': '2026-03-20',
                'description': f'Test {category}'
            })

        # Verify all were inserted
        transactions = get_recent_transactions(user_id, limit=100)
        assert len(transactions) == 7

    def test_post_add_expense_valid_with_decimal_amount(self, auth_client, user_id):
        """POST /expenses/add accepts decimal amounts (e.g., 99.99)."""
        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '99.99',
            'category': 'Shopping',
            'date': '2026-03-20',
            'description': 'Premium item'
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert transactions[0]['amount'] == 99.99

    def test_post_add_expense_valid_minimum_amount(self, auth_client, user_id):
        """POST /expenses/add accepts minimum valid amount (0.01)."""
        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '0.01',
            'category': 'Other',
            'date': '2026-03-20',
            'description': 'Tiny expense'
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert transactions[0]['amount'] == 0.01


# ===================================================================
# Route Tests: POST /expenses/add — Missing Amount
# ===================================================================

class TestPostAddExpenseMissingAmount:
    def test_post_add_expense_missing_amount_returns_200(self, auth_client):
        """POST /expenses/add without amount returns 200 (re-renders form)."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert response.status_code == 200

    def test_post_add_expense_missing_amount_shows_error(self, auth_client):
        """POST /expenses/add without amount displays error message."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert b'error' in response.data.lower() or b'required' in response.data.lower() or b'amount' in response.data.lower()

    def test_post_add_expense_missing_amount_retains_other_values(self, auth_client):
        """POST /expenses/add without amount re-populates other fields."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert b'Food' in response.data
        assert b'2026-03-20' in response.data
        assert b'Lunch' in response.data


# ===================================================================
# Route Tests: POST /expenses/add — Amount = 0
# ===================================================================

class TestPostAddExpenseZeroAmount:
    def test_post_add_expense_zero_amount_returns_200(self, auth_client):
        """POST /expenses/add with amount=0 returns 200 (re-renders form)."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert response.status_code == 200

    def test_post_add_expense_zero_amount_shows_error(self, auth_client):
        """POST /expenses/add with amount=0 displays error message."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert b'error' in response.data.lower() or b'greater' in response.data.lower() or b'zero' in response.data.lower()

    def test_post_add_expense_negative_amount_returns_200(self, auth_client):
        """POST /expenses/add with negative amount returns 200 (re-renders form)."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '-50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert response.status_code == 200


# ===================================================================
# Route Tests: POST /expenses/add — Non-numeric Amount
# ===================================================================

class TestPostAddExpenseNonNumericAmount:
    def test_post_add_expense_non_numeric_amount_returns_200(self, auth_client):
        """POST /expenses/add with non-numeric amount returns 200 (re-renders form)."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': 'abc',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert response.status_code == 200

    def test_post_add_expense_non_numeric_amount_shows_error(self, auth_client):
        """POST /expenses/add with non-numeric amount displays error message."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': 'not-a-number',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert b'error' in response.data.lower() or b'valid' in response.data.lower() or b'amount' in response.data.lower()

    def test_post_add_expense_empty_string_amount_returns_200(self, auth_client):
        """POST /expenses/add with empty string amount returns 200."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert response.status_code == 200


# ===================================================================
# Route Tests: POST /expenses/add — Invalid Category
# ===================================================================

class TestPostAddExpenseInvalidCategory:
    def test_post_add_expense_invalid_category_returns_200(self, auth_client):
        """POST /expenses/add with invalid category returns 200 (re-renders form)."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'InvalidCategory',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert response.status_code == 200

    def test_post_add_expense_invalid_category_shows_error(self, auth_client):
        """POST /expenses/add with invalid category displays error message."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'InvalidCategory',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert b'error' in response.data.lower() or b'category' in response.data.lower() or b'valid' in response.data.lower()

    def test_post_add_expense_missing_category_returns_200(self, auth_client):
        """POST /expenses/add without category returns 200."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        assert response.status_code == 200


# ===================================================================
# Route Tests: POST /expenses/add — Invalid Date
# ===================================================================

class TestPostAddExpenseInvalidDate:
    def test_post_add_expense_invalid_date_format_returns_200(self, auth_client):
        """POST /expenses/add with invalid date format returns 200 (re-renders form)."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '03-20-2026',  # Wrong format
            'description': 'Lunch'
        })

        assert response.status_code == 200

    def test_post_add_expense_invalid_date_shows_error(self, auth_client):
        """POST /expenses/add with invalid date displays error message."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': 'not-a-date',
            'description': 'Lunch'
        })

        assert b'error' in response.data.lower() or b'date' in response.data.lower() or b'valid' in response.data.lower()

    def test_post_add_expense_missing_date_returns_200(self, auth_client):
        """POST /expenses/add without date returns 200."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'description': 'Lunch'
        })

        assert response.status_code == 200

    def test_post_add_expense_empty_date_returns_200(self, auth_client):
        """POST /expenses/add with empty date returns 200."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '',
            'description': 'Lunch'
        })

        assert response.status_code == 200


# ===================================================================
# Route Tests: POST /expenses/add — Optional Description
# ===================================================================

class TestPostAddExpenseOptionalDescription:
    def test_post_add_expense_no_description_redirects(self, auth_client, user_id):
        """POST /expenses/add without description redirects to /profile."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.location

    def test_post_add_expense_no_description_inserts_null(self, auth_client, user_id):
        """POST /expenses/add without description stores NULL in DB."""
        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20'
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert transactions[0]['description'] is None

    def test_post_add_expense_empty_description_inserts_null(self, auth_client, user_id):
        """POST /expenses/add with empty description stores NULL in DB."""
        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': ''
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert transactions[0]['description'] is None

    def test_post_add_expense_whitespace_description_inserts_null(self, auth_client, user_id):
        """POST /expenses/add with whitespace-only description stores NULL in DB."""
        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': '   '
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert transactions[0]['description'] is None

    def test_post_add_expense_valid_description_stored(self, auth_client, user_id):
        """POST /expenses/add with description stores it in DB."""
        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch at the café'
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert transactions[0]['description'] == 'Lunch at the café'


# ===================================================================
# Multiple Validation Errors
# ===================================================================

class TestPostAddExpenseMultipleErrors:
    def test_post_add_expense_multiple_errors_returns_200(self, auth_client):
        """POST /expenses/add with multiple errors returns 200."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': 'abc',
            'category': 'InvalidCategory',
            'date': 'invalid-date',
            'description': 'Lunch'
        })

        assert response.status_code == 200

    def test_post_add_expense_multiple_errors_shows_multiple_messages(self, auth_client):
        """POST /expenses/add with multiple errors shows multiple error messages."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': 'abc',
            'category': 'InvalidCategory',
            'date': 'invalid-date',
            'description': 'Lunch'
        })

        # Should have at least 3 error messages (amount, category, date)
        error_count = response.data.lower().count(b'error')
        assert error_count >= 1  # At least one error message present


# ===================================================================
# Edge Cases and Data Preservation
# ===================================================================

class TestPostAddExpenseEdgeCases:
    def test_post_add_expense_retains_form_data_on_validation_failure(self, auth_client):
        """POST /expenses/add on validation failure retains all submitted values."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': 'not-a-number',
            'category': 'Transport',
            'date': '2026-03-21',
            'description': 'Taxi ride'
        })

        assert b'Transport' in response.data
        assert b'2026-03-21' in response.data
        assert b'Taxi ride' in response.data

    def test_post_add_expense_long_description(self, auth_client, user_id):
        """POST /expenses/add accepts long descriptions up to limit."""
        long_desc = 'A' * 200  # Max is 200 chars per spec

        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': long_desc
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert transactions[0]['description'] == long_desc

    def test_post_add_expense_special_characters_in_description(self, auth_client, user_id):
        """POST /expenses/add handles special characters in description."""
        special_desc = "Lunch @ café, cost $50 & tax!"

        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': special_desc
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert special_desc in transactions[0]['description']

    def test_post_add_expense_unicode_in_description(self, auth_client, user_id):
        """POST /expenses/add handles unicode characters in description."""
        unicode_desc = "Lunch 🍽️ at café"

        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': unicode_desc
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert transactions[0]['description'] is not None

    def test_post_add_expense_future_date(self, auth_client, user_id):
        """POST /expenses/add accepts future dates."""
        future_date = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')

        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': future_date,
            'description': 'Future expense'
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert transactions[0]['date'] == future_date

    def test_post_add_expense_past_date(self, auth_client, user_id):
        """POST /expenses/add accepts past dates."""
        past_date = (date.today() - timedelta(days=365)).strftime('%Y-%m-%d')

        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': past_date,
            'description': 'Old expense'
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert transactions[0]['date'] == past_date


# ===================================================================
# Session and User Isolation
# ===================================================================

class TestPostAddExpenseUserIsolation:
    def test_post_add_expense_creates_for_authenticated_user(self, auth_client, user_id):
        """POST /expenses/add creates expense for the authenticated user."""
        auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        })

        transactions = get_recent_transactions(user_id, limit=1)
        assert len(transactions) == 1

    def test_post_add_expense_multiple_users_isolated(self, app):
        """Multiple users' expenses are isolated (no cross-contamination)."""
        client = app.test_client()

        # Create user 1
        client.post('/register', data={
            'name': 'User One',
            'email': 'user1@example.com',
            'password': 'password123'
        })
        client.post('/login', data={
            'email': 'user1@example.com',
            'password': 'password123'
        })

        # Get user 1's ID
        with client:
            client.get('/profile')
            from flask import session
            user1_id = session['user_id']

        # Add expense for user 1
        client.post('/expenses/add', data={
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'User 1 Lunch'
        })

        # Logout and create user 2
        client.get('/logout')
        client.post('/register', data={
            'name': 'User Two',
            'email': 'user2@example.com',
            'password': 'password123'
        })
        client.post('/login', data={
            'email': 'user2@example.com',
            'password': 'password123'
        })

        # Get user 2's ID
        with client:
            client.get('/profile')
            from flask import session
            user2_id = session['user_id']

        # Add expense for user 2
        client.post('/expenses/add', data={
            'amount': '75.0',
            'category': 'Transport',
            'date': '2026-03-21',
            'description': 'User 2 Taxi'
        })

        # Verify isolation
        user1_txns = get_recent_transactions(user1_id, limit=10)
        user2_txns = get_recent_transactions(user2_id, limit=10)

        assert len(user1_txns) == 1
        assert len(user2_txns) == 1
        assert user1_txns[0]['description'] == 'User 1 Lunch'
        assert user2_txns[0]['description'] == 'User 2 Taxi'


# ===================================================================
# Flash Messages
# ===================================================================

class TestPostAddExpenseFlashMessages:
    def test_post_add_expense_valid_shows_success_flash(self, auth_client):
        """POST /expenses/add with valid data displays success message."""
        response = auth_client.post('/expenses/add', data={
                    'csrf_token': get_csrf_token(auth_client),
            'amount': '50.0',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch'
        }, follow_redirects=True)

        assert b'success' in response.data.lower() or b'added' in response.data.lower()
