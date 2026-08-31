import pytest
import os
from app import app as flask_app
from database.db import init_db, get_db
from database.queries import insert_expense, get_expense_by_id, delete_expense
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='function')
def app():
    """Create and configure a test Flask app with fresh DB per test."""
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
    })
    db_path = 'spendly.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    with flask_app.app_context():
        init_db()
        yield flask_app

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
# Unit Tests: delete_expense
# ===================================================================

class TestDeleteExpenseUnit:
    def test_delete_expense_valid_user(self, user1):
        """delete_expense removes the row when user owns the expense."""
        expense_id = insert_expense(user1, 50.0, 'Food', '2026-08-15', 'Lunch')

        # Verify expense exists
        assert get_expense_by_id(expense_id, user1) is not None

        # Delete it
        rows_affected = delete_expense(expense_id, user1)

        # Verify row was deleted
        assert rows_affected == 1
        assert get_expense_by_id(expense_id, user1) is None

    def test_delete_expense_wrong_user(self, user1, user2):
        """delete_expense does not delete if user_id doesn't match."""
        expense_id = insert_expense(user1, 50.0, 'Food', '2026-08-15', 'Lunch')

        # Try to delete with wrong user
        rows_affected = delete_expense(expense_id, user2)

        # Verify nothing was deleted
        assert rows_affected == 0
        # Expense should still exist for user1
        assert get_expense_by_id(expense_id, user1) is not None

    def test_delete_expense_nonexistent(self, user1):
        """delete_expense handles non-existent expense_id gracefully."""
        rows_affected = delete_expense(99999, user1)

        # Should return 0, no error raised
        assert rows_affected == 0


# ===================================================================
# Route Tests: POST /expenses/<id>/delete
# ===================================================================

class TestDeleteExpenseRoute:
    def test_delete_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated POST to delete redirects to login."""
        response = client.post('/expenses/1/delete', follow_redirects=False)

        assert response.status_code == 302
        assert '/login' in response.location

    def test_delete_own_expense_success(self, auth_client, user_id, app):
        """Authenticated user can delete their own expense."""
        # Insert an expense for the authenticated user
        with app.app_context():
            expense_id = insert_expense(user_id, 75.0, 'Transport', '2026-08-20', 'Taxi')

        # Delete it via POST
        response = auth_client.post(f'/expenses/{expense_id}/delete', follow_redirects=False)

        # Verify redirect to profile
        assert response.status_code == 302
        assert response.location == '/profile'

        # Verify expense is actually deleted
        with app.app_context():
            assert get_expense_by_id(expense_id, user_id) is None

    def test_delete_own_expense_flash_message(self, auth_client, user_id, app):
        """Successful delete shows flash message on profile."""
        with app.app_context():
            expense_id = insert_expense(user_id, 75.0, 'Transport', '2026-08-20', 'Taxi')

        # Delete and follow redirect
        response = auth_client.post(f'/expenses/{expense_id}/delete', follow_redirects=True)

        # Verify flash message appears in response
        assert response.status_code == 200
        assert 'Expense deleted successfully' in response.data.decode()

    def test_delete_other_user_expense_404(self, auth_client, user1, user2, app):
        """Attempting to delete another user's expense returns 404."""
        with app.app_context():
            expense_id = insert_expense(user1, 50.0, 'Food', '2026-08-15', 'Lunch')

        # Try to delete with authenticated user (user2)
        response = auth_client.post(f'/expenses/{expense_id}/delete', follow_redirects=False)

        # Should get 404
        assert response.status_code == 404

    def test_delete_nonexistent_expense_404(self, auth_client):
        """Attempting to delete non-existent expense returns 404."""
        response = auth_client.post('/expenses/99999/delete', follow_redirects=False)

        assert response.status_code == 404

    def test_delete_get_request_405(self, auth_client, user_id, app):
        """GET request to delete endpoint returns 405."""
        with app.app_context():
            expense_id = insert_expense(user_id, 75.0, 'Transport', '2026-08-20', 'Taxi')

        response = auth_client.get(f'/expenses/{expense_id}/delete', follow_redirects=False)

        # Should get 405 Method Not Allowed
        assert response.status_code == 405

    def test_delete_expense_actually_removed_from_db(self, auth_client, user_id, app):
        """Verify expense row is actually removed from database after delete."""
        with app.app_context():
            expense_id = insert_expense(user_id, 100.0, 'Shopping', '2026-08-25', 'Shoes')

            # Verify it exists
            assert get_expense_by_id(expense_id, user_id) is not None

        # Delete via route
        auth_client.post(f'/expenses/{expense_id}/delete')

        # Verify it's gone from DB
        with app.app_context():
            assert get_expense_by_id(expense_id, user_id) is None
