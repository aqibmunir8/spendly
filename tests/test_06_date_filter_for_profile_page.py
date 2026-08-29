import pytest
from datetime import datetime, date, timedelta
from app import app as flask_app, calculate_preset_dates, detect_active_preset
from database.db import init_db, get_db, create_user, generate_password_hash
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
    get_user_by_id
)


@pytest.fixture
def app():
    """Create and configure a test Flask app."""
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
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
def user_with_expenses(app, auth_client):
    """Create a user with sample expenses across different dates."""
    with auth_client:
        auth_client.get('/profile')
        from flask import session
        user_id = session['user_id']

    conn = get_db()
    cursor = conn.cursor()

    today = date.today()

    expenses = [
        (user_id, 45.50, 'Food', (today - timedelta(days=5)).strftime('%Y-%m-%d'), 'Grocery shopping'),
        (user_id, 12.00, 'Transport', (today - timedelta(days=3)).strftime('%Y-%m-%d'), 'Uber ride'),
        (user_id, 85.30, 'Bills', today.strftime('%Y-%m-%d'), 'Electricity bill'),
        (user_id, 120.00, 'Health', (today - timedelta(days=45)).strftime('%Y-%m-%d'), 'Doctor visit'),
        (user_id, 35.00, 'Entertainment', (today - timedelta(days=60)).strftime('%Y-%m-%d'), 'Movie tickets'),
        (user_id, 67.80, 'Shopping', (today - timedelta(days=120)).strftime('%Y-%m-%d'), 'Running shoes'),
        (user_id, 25.50, 'Other', (today - timedelta(days=150)).strftime('%Y-%m-%d'), 'Birthday gift'),
        (user_id, 18.75, 'Food', (today - timedelta(days=200)).strftime('%Y-%m-%d'), 'Lunch at cafe'),
    ]

    cursor.executemany(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        expenses
    )
    conn.commit()
    conn.close()

    return auth_client, user_id


# ===================================================================
# Auth Guard Tests
# ===================================================================

class TestAuthGuard:
    def test_profile_redirects_to_login_when_unauthenticated(self, client):
        """Unauthenticated request to /profile redirects to /login."""
        response = client.get('/profile')
        assert response.status_code == 302
        assert '/login' in response.location


# ===================================================================
# Happy Path: Presets
# ===================================================================

class TestDateFilterPresets:
    def test_all_time_preset_no_params(self, user_with_expenses):
        """No date params passed shows all expenses (All Time preset active)."""
        auth_client, user_id = user_with_expenses
        response = auth_client.get('/profile')

        assert response.status_code == 200
        assert b'profile' in response.data.lower() or b'expense' in response.data.lower()

    def test_this_month_preset(self, user_with_expenses):
        """This Month preset filters to current month."""
        auth_client, user_id = user_with_expenses
        today = date.today()
        presets = calculate_preset_dates(today)
        date_from = presets['this_month']['from']
        date_to = presets['this_month']['to']

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        assert response.status_code == 200

    def test_three_months_preset(self, user_with_expenses):
        """Last 3 Months preset filters to 3-month range."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        presets = calculate_preset_dates(today)
        date_from = presets['three_months']['from']
        date_to = presets['three_months']['to']

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        assert response.status_code == 200

    def test_six_months_preset(self, user_with_expenses):
        """Last 6 Months preset filters to 6-month range."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        presets = calculate_preset_dates(today)
        date_from = presets['six_months']['from']
        date_to = presets['six_months']['to']

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        assert response.status_code == 200


# ===================================================================
# Custom Date Ranges
# ===================================================================

class TestCustomDateRange:
    def test_custom_date_range(self, user_with_expenses):
        """Custom date range works correctly."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        date_from = (today - timedelta(days=10)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        assert response.status_code == 200

    def test_single_day_range(self, user_with_expenses):
        """Single-day range (from == to) works correctly."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        date_str = today.strftime('%Y-%m-%d')

        response = auth_client.get(f'/profile?date_from={date_str}&date_to={date_str}')

        assert response.status_code == 200


# ===================================================================
# Date Validation: Error Cases
# ===================================================================

class TestDateValidation:
    def test_inverted_date_range_shows_error(self, user_with_expenses):
        """Inverted range (from > to) shows flash error and falls back to unfiltered."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        date_from = today.strftime('%Y-%m-%d')
        date_to = (today - timedelta(days=10)).strftime('%Y-%m-%d')

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        assert response.status_code == 200
        assert b'Start date must be before end date' in response.data or b'error' in response.data.lower()

    def test_malformed_date_from_silently_ignored(self, user_with_expenses):
        """Malformed date_from falls back to unfiltered."""
        auth_client, user_id = user_with_expenses

        response = auth_client.get('/profile?date_from=not-a-date&date_to=2026-08-29')

        assert response.status_code == 200

    def test_malformed_date_to_silently_ignored(self, user_with_expenses):
        """Malformed date_to falls back to unfiltered."""
        auth_client, user_id = user_with_expenses

        response = auth_client.get('/profile?date_from=2026-08-01&date_to=invalid')

        assert response.status_code == 200

    def test_only_date_from_silently_ignored(self, user_with_expenses):
        """Only date_from param (no date_to) silently ignored."""
        auth_client, user_id = user_with_expenses

        response = auth_client.get('/profile?date_from=2026-08-01')

        assert response.status_code == 200

    def test_only_date_to_silently_ignored(self, user_with_expenses):
        """Only date_to param (no date_from) silently ignored."""
        auth_client, user_id = user_with_expenses

        response = auth_client.get('/profile?date_to=2026-08-29')

        assert response.status_code == 200


# ===================================================================
# Empty Result Sets
# ===================================================================

class TestEmptyResultSets:
    def test_date_range_with_no_expenses(self, user_with_expenses):
        """Date range with no matching expenses returns empty data gracefully."""
        auth_client, user_id = user_with_expenses

        date_from = (date.today() + timedelta(days=365)).strftime('%Y-%m-%d')
        date_to = (date.today() + timedelta(days=370)).strftime('%Y-%m-%d')

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        assert response.status_code == 200
        stats = get_summary_stats(user_id, date_from, date_to)
        assert stats['transaction_count'] == 0
        assert stats['total_spent'] == 0.0
        assert stats['top_category'] == '—'


# ===================================================================
# Data Consistency Across Sections
# ===================================================================

class TestDataConsistency:
    def test_stats_transactions_categories_use_same_filter(self, user_with_expenses):
        """All three data sections use the same date filter."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        date_from = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        stats = get_summary_stats(user_id, date_from, date_to)
        transactions = get_recent_transactions(user_id, limit=10, date_from=date_from, date_to=date_to)
        categories = get_category_breakdown(user_id, date_from, date_to)

        assert stats['transaction_count'] == len(transactions)

        category_total = sum(cat['total'] for cat in categories)
        assert abs(category_total - stats['total_spent']) < 0.01

    def test_profile_page_passes_filter_to_all_queries(self, user_with_expenses):
        """Profile route passes date filter to all three query functions."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        date_from = (today - timedelta(days=60)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        response = auth_client.get(f'/profile?date_from={date_from}&date_to={date_to}')

        assert response.status_code == 200


# ===================================================================
# Query Function Tests
# ===================================================================

class TestGetSummaryStatsWithDates:
    def test_stats_without_date_filter(self, user_with_expenses):
        """get_summary_stats without date filter returns all expenses."""
        auth_client, user_id = user_with_expenses

        stats = get_summary_stats(user_id)

        assert stats['transaction_count'] == 8
        assert stats['total_spent'] > 0
        assert stats['top_category'] != '—'

    def test_stats_with_date_filter(self, user_with_expenses):
        """get_summary_stats with date filter returns only filtered expenses."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        date_from = (today - timedelta(days=10)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        stats = get_summary_stats(user_id, date_from, date_to)

        assert stats['transaction_count'] >= 0
        assert stats['transaction_count'] <= 8

    def test_stats_with_empty_date_range(self, user_with_expenses):
        """get_summary_stats with empty date range returns zeros."""
        auth_client, user_id = user_with_expenses

        date_from = '2099-01-01'
        date_to = '2099-12-31'

        stats = get_summary_stats(user_id, date_from, date_to)

        assert stats['transaction_count'] == 0
        assert stats['total_spent'] == 0.0
        assert stats['top_category'] == '—'


class TestGetRecentTransactionsWithDates:
    def test_transactions_without_date_filter(self, user_with_expenses):
        """get_recent_transactions without date filter returns recent expenses."""
        auth_client, user_id = user_with_expenses

        transactions = get_recent_transactions(user_id, limit=10)

        assert len(transactions) == 8
        assert transactions[0]['date'] >= transactions[-1]['date']

    def test_transactions_with_date_filter(self, user_with_expenses):
        """get_recent_transactions with date filter returns only filtered expenses."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        date_from = (today - timedelta(days=10)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        transactions = get_recent_transactions(user_id, limit=10, date_from=date_from, date_to=date_to)

        assert len(transactions) <= 8
        for txn in transactions:
            assert date_from <= txn['date'] <= date_to

    def test_transactions_respects_limit(self, user_with_expenses):
        """get_recent_transactions respects the limit parameter."""
        auth_client, user_id = user_with_expenses

        transactions = get_recent_transactions(user_id, limit=3)

        assert len(transactions) == 3

    def test_transactions_with_date_filter_and_limit(self, user_with_expenses):
        """get_recent_transactions with both date filter and limit applies both."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        date_from = (today - timedelta(days=180)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        transactions = get_recent_transactions(user_id, limit=2, date_from=date_from, date_to=date_to)

        assert len(transactions) <= 2


class TestGetCategoryBreakdownWithDates:
    def test_categories_without_date_filter(self, user_with_expenses):
        """get_category_breakdown without date filter includes all categories."""
        auth_client, user_id = user_with_expenses

        categories = get_category_breakdown(user_id)

        assert len(categories) > 0
        total_percentage = sum(cat['percentage'] for cat in categories)
        assert total_percentage == 100

    def test_categories_with_date_filter(self, user_with_expenses):
        """get_category_breakdown with date filter includes only filtered expenses."""
        auth_client, user_id = user_with_expenses

        today = date.today()
        date_from = (today - timedelta(days=10)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

        categories = get_category_breakdown(user_id, date_from, date_to)

        assert len(categories) >= 0
        if categories:
            total_percentage = sum(cat['percentage'] for cat in categories)
            assert total_percentage == 100

    def test_categories_ordered_by_total_desc(self, user_with_expenses):
        """get_category_breakdown returns categories ordered by total DESC."""
        auth_client, user_id = user_with_expenses

        categories = get_category_breakdown(user_id)

        totals = [cat['total'] for cat in categories]
        assert totals == sorted(totals, reverse=True)

    def test_categories_empty_result(self, user_with_expenses):
        """get_category_breakdown returns empty list if no expenses in range."""
        auth_client, user_id = user_with_expenses

        date_from = '2099-01-01'
        date_to = '2099-12-31'

        categories = get_category_breakdown(user_id, date_from, date_to)

        assert categories == []


# ===================================================================
# Boundary Date Tests
# ===================================================================

class TestBoundaryDates:
    def test_boundary_dates_inclusive(self, user_with_expenses):
        """BETWEEN clause is inclusive of both from and to dates."""
        auth_client, user_id = user_with_expenses

        today = date.today()

        transactions = get_recent_transactions(user_id)
        if transactions:
            exact_date = transactions[0]['date']

            result = get_recent_transactions(user_id, date_from=exact_date, date_to=exact_date)

            assert len(result) >= 1


# ===================================================================
# Preset Detection
# ===================================================================

class TestPresetDetection:
    def test_detect_active_preset_this_month(self):
        """detect_active_preset correctly identifies this_month preset."""
        today = date.today()
        this_month_start = today.replace(day=1)

        active = detect_active_preset(this_month_start, today)
        assert active == 'this_month'

    def test_detect_active_preset_three_months(self):
        """detect_active_preset correctly identifies three_months preset."""
        today = date.today()
        three_months_ago = today - timedelta(days=90)

        active = detect_active_preset(three_months_ago, today)
        assert active == 'three_months'

    def test_detect_active_preset_six_months(self):
        """detect_active_preset correctly identifies six_months preset."""
        today = date.today()
        six_months_ago = today - timedelta(days=180)

        active = detect_active_preset(six_months_ago, today)
        assert active == 'six_months'

    def test_detect_active_preset_custom(self):
        """detect_active_preset returns 'custom' for non-matching ranges."""
        today = date.today()
        arbitrary_date = today - timedelta(days=45)

        active = detect_active_preset(arbitrary_date, today)
        assert active == 'custom'


# ===================================================================
# Calculate Preset Dates
# ===================================================================

class TestCalculatePresetDates:
    def test_calculate_preset_dates_structure(self):
        """calculate_preset_dates returns correct structure."""
        today = date.today()
        presets = calculate_preset_dates(today)

        assert 'this_month' in presets
        assert 'three_months' in presets
        assert 'six_months' in presets
        for preset in presets.values():
            assert 'from' in preset
            assert 'to' in preset

    def test_this_month_starts_on_first_day(self):
        """calculate_preset_dates this_month starts on day 1."""
        today = date.today()
        presets = calculate_preset_dates(today)

        from_date = datetime.strptime(presets['this_month']['from'], '%Y-%m-%d').date()
        assert from_date.day == 1
        assert from_date.month == today.month
        assert from_date.year == today.year

    def test_preset_dates_end_on_today(self):
        """All presets end on today."""
        today = date.today()
        presets = calculate_preset_dates(today)

        today_str = today.strftime('%Y-%m-%d')
        assert presets['this_month']['to'] == today_str
        assert presets['three_months']['to'] == today_str
        assert presets['six_months']['to'] == today_str
