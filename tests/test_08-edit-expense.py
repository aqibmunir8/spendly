import pytest
import os
from datetime import date, datetime, timedelta
from app import app as flask_app
from database.db import init_db, get_db, create_user
from database.queries import insert_expense, get_recent_transactions, get_expense_by_id, update_expense
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='function')
def app():
    """Create and configure a test Flask app with fresh DB per test."""
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
    })
    # Remove any existing test DB to ensure clean state
    db_path = 'spendly.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    with flask_app.app_context():
        init_db()
        yield flask_app

    # Clean up after test
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope='function')
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def user1(app):
    """Create first user directly in DB and return user_id."""
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            ('User One', 'user1@test.com', generate_password_hash('pass123'))
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
    return user_id


@pytest.fixture(scope='function')
def user2(app):
    """Create second user directly in DB and return user_id."""
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            ('User Two', 'user2@test.com', generate_password_hash('pass456'))
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
    return user_id


@pytest.fixture(scope='function')
def auth_client(client):
    """Create a test client that is already logged in as user1."""
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


@pytest.fixture(scope='function')
def user_id(auth_client):
    """Extract user_id from authenticated session."""
    with auth_client:
        auth_client.get('/profile')
        from flask import session
        return session['user_id']


# ===================================================================
# Unit Tests: get_expense_by_id
# ===================================================================

class TestGetExpenseByIdUnit:
    def test_get_expense_by_id_valid_user(self, user1):
        """get_expense_by_id returns the matching row when user owns the expense."""
        expense_id = insert_expense(user1, 100.0, 'Food', '2026-08-15', 'Lunch')
        result = get_expense_by_id(expense_id, user1)
        assert result is not None
        assert result['id'] == expense_id
        assert result['amount'] == 100.0
        assert result['category'] == 'Food'

    def test_get_expense_by_id_wrong_user(self, user1, user2):
        """get_expense_by_id returns None when user doesn't own the expense."""
        expense_id = insert_expense(user1, 100.0, 'Food', '2026-08-15', 'Lunch')
        result = get_expense_by_id(expense_id, user2)
        assert result is None

    def test_get_expense_by_id_non_existent(self, user1):
        """get_expense_by_id returns None when expense doesn't exist."""
        result = get_expense_by_id(999999, user1)
        assert result is None


# ===================================================================
# Unit Tests: update_expense
# ===================================================================

class TestUpdateExpenseUnit:
    def test_update_expense_valid_user(self, user1):
        """update_expense updates the expense when user owns it."""
        expense_id = insert_expense(user1, 100.0, 'Food', '2026-08-15', 'Lunch')
        update_expense(expense_id, user1, 150.0, 'Transport', '2026-08-20', 'Commute')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT amount, category, description FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['amount'] == 150.0
        assert row['category'] == 'Transport'
        assert row['description'] == 'Commute'

    def test_update_expense_wrong_user(self, user1, user2):
        """update_expense doesn't update when user doesn't own the expense."""
        expense_id = insert_expense(user1, 100.0, 'Food', '2026-08-15', 'Lunch')
        update_expense(expense_id, user2, 200.0, 'Shopping', '2026-08-25', 'Updated')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT amount, category, description FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['amount'] == 100.0
        assert row['category'] == 'Food'
        assert row['description'] == 'Lunch'


# ===================================================================
# Route Tests: GET /expenses/<id>/edit
# ===================================================================

class TestEditExpenseRouteGET:
    def test_get_edit_expense_unauthenticated(self, client):
        """GET /expenses/<id>/edit redirects to login when unauthenticated."""
        response = client.get('/expenses/1/edit')
        assert response.status_code == 302
        assert '/login' in response.headers.get('Location', '')

    def test_get_edit_expense_authenticated_own_expense(self, auth_client, user_id):
        """GET /expenses/<id>/edit returns form with pre-filled values when user owns the expense."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')
        response = auth_client.get(f'/expenses/{expense_id}/edit')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert '<form' in html
        assert 'method="POST"' in html
        assert 'Food' in html
        assert '2026-08-15' in html

    def test_get_edit_expense_authenticated_other_user(self, app, auth_client, user_id):
        """GET /expenses/<id>/edit returns 404 when user tries to edit another user's expense."""
        # Create another user and an expense
        with app.app_context():
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                ('Other User', 'other@test.com', generate_password_hash('otherpass'))
            )
            other_user_id = cursor.lastrowid
            conn.commit()
            conn.close()

        expense_id = insert_expense(other_user_id, 100.0, 'Food', '2026-08-15', 'Lunch')
        response = auth_client.get(f'/expenses/{expense_id}/edit')
        assert response.status_code == 404

    def test_get_edit_expense_authenticated_non_existent(self, auth_client):
        """GET /expenses/<id>/edit returns 404 when expense doesn't exist."""
        response = auth_client.get('/expenses/999999/edit')
        assert response.status_code == 404


# ===================================================================
# Route Tests: POST /expenses/<id>/edit
# ===================================================================

class TestEditExpenseRoutePOST:
    def test_post_edit_expense_unauthenticated(self, client):
        """POST /expenses/<id>/edit redirects to login when unauthenticated."""
        response = client.post('/expenses/1/edit', data={
            'csrf_token': 'dummy-token',
            'amount': '50.00',
            'category': 'Food',
            'date': '2026-08-15',
            'description': 'Test'
        })
        assert response.status_code == 302
        assert '/login' in response.headers.get('Location', '')

    def test_post_edit_expense_authenticated_valid(self, auth_client, user_id):
        """POST /expenses/<id>/edit redirects to profile and updates DB when user submits valid data."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '150.00',
            'category': 'Transport',
            'date': '2026-08-20',
            'description': 'Updated expense'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers.get('Location', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT amount, category, description FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['amount'] == 150.0
        assert row['category'] == 'Transport'
        assert row['description'] == 'Updated expense'

    def test_post_edit_expense_authenticated_other_user(self, app, auth_client, user_id):
        """POST /expenses/<id>/edit returns 404 when user tries to update another user's expense."""
        # Create another user and an expense
        with app.app_context():
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                ('Other User', 'other@test.com', generate_password_hash('otherpass'))
            )
            other_user_id = cursor.lastrowid
            conn.commit()
            conn.close()

        expense_id = insert_expense(other_user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '200.00',
            'category': 'Shopping',
            'date': '2026-08-25',
            'description': 'Hacked'
        })

        assert response.status_code == 404

    def test_post_edit_expense_authenticated_missing_amount(self, auth_client, user_id):
        """POST /expenses/<id>/edit re-renders form with error when amount is missing."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '',
            'category': 'Food',
            'date': '2026-08-20',
            'description': 'Test'
        })

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Amount is required' in html

    def test_post_edit_expense_authenticated_amount_zero(self, auth_client, user_id):
        """POST /expenses/<id>/edit re-renders form with error when amount is zero."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '0',
            'category': 'Food',
            'date': '2026-08-20',
            'description': 'Test'
        })

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Amount must be greater than zero' in html

    def test_post_edit_expense_authenticated_non_numeric_amount(self, auth_client, user_id):
        """POST /expenses/<id>/edit re-renders form with error when amount is non-numeric."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': 'abc',
            'category': 'Food',
            'date': '2026-08-20',
            'description': 'Test'
        })

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Amount must be a valid number' in html

    def test_post_edit_expense_authenticated_invalid_category(self, auth_client, user_id):
        """POST /expenses/<id>/edit re-renders form with error when category is invalid."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '50.00',
            'category': 'InvalidCategory',
            'date': '2026-08-20',
            'description': 'Test'
        })

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Invalid category selected' in html

    def test_post_edit_expense_authenticated_invalid_date(self, auth_client, user_id):
        """POST /expenses/<id>/edit re-renders form with error when date is invalid."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '50.00',
            'category': 'Food',
            'date': '2099-08-20',
            'description': 'Test'
        })

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Date cannot be in the future' in html

    def test_post_edit_expense_authenticated_no_description(self, auth_client, user_id):
        """POST /expenses/<id>/edit redirects to profile when description is missing (should save as NULL)."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '50.00',
            'category': 'Food',
            'date': '2026-08-20',
            'description': ''
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers.get('Location', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT description FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['description'] is None


# ===================================================================
# Unit Tests: get_expense_by_id
# ===================================================================

class TestGetExpenseByIdUnit:
    def test_get_expense_by_id_valid_user(self, user1):
        """get_expense_by_id returns the matching row when user owns the expense."""
        expense_id = insert_expense(user1, 100.0, 'Food', '2026-08-15', 'Lunch')
        result = get_expense_by_id(expense_id, user1)
        assert result is not None
        assert result['id'] == expense_id
        assert result['amount'] == 100.0
        assert result['category'] == 'Food'

    def test_get_expense_by_id_wrong_user(self, user1, user2):
        """get_expense_by_id returns None when user doesn't own the expense."""
        expense_id = insert_expense(user1, 100.0, 'Food', '2026-08-15', 'Lunch')
        result = get_expense_by_id(expense_id, user2)
        assert result is None

    def test_get_expense_by_id_non_existent(self, user1):
        """get_expense_by_id returns None when expense doesn't exist."""
        result = get_expense_by_id(999999, user1)
        assert result is None


# ===================================================================
# Unit Tests: update_expense
# ===================================================================

class TestUpdateExpenseUnit:
    def test_update_expense_valid_user(self, user1):
        """update_expense updates the expense when user owns it."""
        expense_id = insert_expense(user1, 100.0, 'Food', '2026-08-15', 'Lunch')
        update_expense(expense_id, user1, 150.0, 'Transport', '2026-08-20', 'Commute')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT amount, category, description FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['amount'] == 150.0
        assert row['category'] == 'Transport'
        assert row['description'] == 'Commute'

    def test_update_expense_wrong_user(self, user1, user2):
        """update_expense doesn't update when user doesn't own the expense."""
        expense_id = insert_expense(user1, 100.0, 'Food', '2026-08-15', 'Lunch')
        update_expense(expense_id, user2, 200.0, 'Shopping', '2026-08-25', 'Updated')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT amount, category, description FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['amount'] == 100.0
        assert row['category'] == 'Food'
        assert row['description'] == 'Lunch'


# ===================================================================
# Route Tests: GET /expenses/<id>/edit
# ===================================================================

class TestEditExpenseRouteGET:
    def test_get_edit_expense_unauthenticated(self, client):
        """GET /expenses/<id>/edit redirects to login when unauthenticated."""
        response = client.get('/expenses/1/edit')
        assert response.status_code == 302
        assert '/login' in response.headers.get('Location', '')

    def test_get_edit_expense_authenticated_own_expense(self, auth_client, user_id):
        """GET /expenses/<id>/edit returns form with pre-filled values when user owns the expense."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')
        response = auth_client.get(f'/expenses/{expense_id}/edit')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert '<form' in html
        assert 'method="POST"' in html
        assert 'Food' in html
        assert '2026-08-15' in html

    def test_get_edit_expense_authenticated_other_user(self, app, auth_client, user_id):
        """GET /expenses/<id>/edit returns 404 when user tries to edit another user's expense."""
        # Create another user and an expense
        with app.app_context():
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                ('Other User', 'other@test.com', generate_password_hash('otherpass'))
            )
            other_user_id = cursor.lastrowid
            conn.commit()
            conn.close()

        expense_id = insert_expense(other_user_id, 100.0, 'Food', '2026-08-15', 'Lunch')
        response = auth_client.get(f'/expenses/{expense_id}/edit')
        assert response.status_code == 404

    def test_get_edit_expense_authenticated_non_existent(self, auth_client):
        """GET /expenses/<id>/edit returns 404 when expense doesn't exist."""
        response = auth_client.get('/expenses/999999/edit')
        assert response.status_code == 404


# ===================================================================
# Route Tests: POST /expenses/<id>/edit
# ===================================================================

class TestEditExpenseRoutePOST:
    def test_post_edit_expense_unauthenticated(self, client):
        """POST /expenses/<id>/edit redirects to login when unauthenticated."""
        response = client.post('/expenses/1/edit', data={
            'csrf_token': 'dummy-token',
            'amount': '50.00',
            'category': 'Food',
            'date': '2026-08-15',
            'description': 'Test'
        })
        assert response.status_code == 302
        assert '/login' in response.headers.get('Location', '')

    def test_post_edit_expense_authenticated_valid(self, auth_client, user_id):
        """POST /expenses/<id>/edit redirects to profile and updates DB when user submits valid data."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '150.00',
            'category': 'Transport',
            'date': '2026-08-20',
            'description': 'Updated expense'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers.get('Location', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT amount, category, description FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['amount'] == 150.0
        assert row['category'] == 'Transport'
        assert row['description'] == 'Updated expense'

    def test_post_edit_expense_authenticated_other_user(self, app, auth_client, user_id):
        """POST /expenses/<id>/edit returns 404 when user tries to update another user's expense."""
        # Create another user and an expense
        with app.app_context():
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                ('Other User', 'other@test.com', generate_password_hash('otherpass'))
            )
            other_user_id = cursor.lastrowid
            conn.commit()
            conn.close()

        expense_id = insert_expense(other_user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '200.00',
            'category': 'Shopping',
            'date': '2026-08-25',
            'description': 'Hacked'
        })

        assert response.status_code == 404

    def test_post_edit_expense_authenticated_missing_amount(self, auth_client, user_id):
        """POST /expenses/<id>/edit re-renders form with error when amount is missing."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '',
            'category': 'Food',
            'date': '2026-08-20',
            'description': 'Test'
        })

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Amount is required' in html

    def test_post_edit_expense_authenticated_amount_zero(self, auth_client, user_id):
        """POST /expenses/<id>/edit re-renders form with error when amount is zero."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '0',
            'category': 'Food',
            'date': '2026-08-20',
            'description': 'Test'
        })

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Amount must be greater than zero' in html

    def test_post_edit_expense_authenticated_non_numeric_amount(self, auth_client, user_id):
        """POST /expenses/<id>/edit re-renders form with error when amount is non-numeric."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': 'abc',
            'category': 'Food',
            'date': '2026-08-20',
            'description': 'Test'
        })

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Amount must be a valid number' in html

    def test_post_edit_expense_authenticated_invalid_category(self, auth_client, user_id):
        """POST /expenses/<id>/edit re-renders form with error when category is invalid."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '50.00',
            'category': 'InvalidCategory',
            'date': '2026-08-20',
            'description': 'Test'
        })

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Invalid category selected' in html

    def test_post_edit_expense_authenticated_invalid_date(self, auth_client, user_id):
        """POST /expenses/<id>/edit re-renders form with error when date is invalid."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '50.00',
            'category': 'Food',
            'date': '2099-08-20',
            'description': 'Test'
        })

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Date cannot be in the future' in html

    def test_post_edit_expense_authenticated_no_description(self, auth_client, user_id):
        """POST /expenses/<id>/edit redirects to profile when description is missing (should save as NULL)."""
        expense_id = insert_expense(user_id, 100.0, 'Food', '2026-08-15', 'Lunch')

        with auth_client:
            auth_client.get(f'/expenses/{expense_id}/edit')
            from flask import session
            csrf_token = session.get('csrf_token', '')

        response = auth_client.post(f'/expenses/{expense_id}/edit', data={
            'csrf_token': csrf_token,
            'amount': '50.00',
            'category': 'Food',
            'date': '2026-08-20',
            'description': ''
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/profile' in response.headers.get('Location', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT description FROM expenses WHERE id = ?', (expense_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['description'] is None