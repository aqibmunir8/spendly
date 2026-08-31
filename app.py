import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
from database.db import init_db, seed_db, get_user_by_email, create_user, verify_password
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown, insert_expense, get_expense_by_id, update_expense, delete_expense

VALID_CATEGORIES = ['Food', 'Transport', 'Bills', 'Health', 'Entertainment', 'Shopping', 'Other']

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')


def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
    return session['csrf_token']


def validate_csrf_token(token):
    return token == session.get('csrf_token')


def validate_expense_form(amount_str, category, date_str, valid_categories):
    """
    Validate expense form inputs. Returns (amount, parsed_date, errors).
    If errors list is non-empty, amount and parsed_date may be None.
    """
    errors = []
    amount = None
    parsed_date = None

    # Amount validation
    if not amount_str:
        errors.append("Amount is required.")
    else:
        try:
            amount = float(amount_str)
            if amount <= 0:
                errors.append("Amount must be greater than zero.")
        except ValueError:
            errors.append("Amount must be a valid number.")

    # Category validation
    if not category:
        errors.append("Category is required.")
    elif category not in valid_categories:
        errors.append("Invalid category selected.")

    # Date validation
    if not date_str:
        errors.append("Date is required.")
    else:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = date.today()
            ten_years_ago = today - timedelta(days=3650)
            if parsed_date > today:
                errors.append("Date cannot be in the future.")
            elif parsed_date < ten_years_ago:
                errors.append("Date cannot be more than 10 years in the past.")
        except ValueError:
            errors.append("Date must be in YYYY-MM-DD format.")

    return amount, parsed_date, errors

with app.app_context():
    init_db()
    seed_db()


@app.context_processor
def inject_user():
    context = {'csrf_token': generate_csrf_token}
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            context['current_user'] = {'name': user['name']}
    return context


def calculate_preset_dates(today):
    """Calculate date ranges for preset filters."""
    this_month_start = today.replace(day=1)
    three_months_ago = today - timedelta(days=90)
    six_months_ago = today - timedelta(days=180)

    return {
        'this_month': {
            'from': this_month_start.strftime('%Y-%m-%d'),
            'to': today.strftime('%Y-%m-%d')
        },
        'three_months': {
            'from': three_months_ago.strftime('%Y-%m-%d'),
            'to': today.strftime('%Y-%m-%d')
        },
        'six_months': {
            'from': six_months_ago.strftime('%Y-%m-%d'),
            'to': today.strftime('%Y-%m-%d')
        }
    }


def detect_active_preset(date_from_obj, date_to_obj):
    """Determine which preset button should be highlighted."""
    today = date.today()
    presets = calculate_preset_dates(today)

    date_from_str = date_from_obj.strftime('%Y-%m-%d')
    date_to_str = date_to_obj.strftime('%Y-%m-%d')

    if (date_from_str == presets['this_month']['from'] and
        date_to_str == presets['this_month']['to']):
        return 'this_month'
    elif (date_from_str == presets['three_months']['from'] and
          date_to_str == presets['three_months']['to']):
        return 'three_months'
    elif (date_from_str == presets['six_months']['from'] and
          date_to_str == presets['six_months']['to']):
        return 'six_months'
    else:
        return 'custom'


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('profile'))
    if request.method == 'GET':
        return render_template("register.html")

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if not name:
        return render_template("register.html", error="Name is required.", name=name, email=email)
    if not email:
        return render_template("register.html", error="Email is required.", name=name, email=email)
    if len(password) < 8:
        return render_template(
            "register.html",
            error="Password must be at least 8 characters.",
            name=name,
            email=email
        )
    if get_user_by_email(email) is not None:
        return render_template(
            "register.html",
            error="An account with this email already exists.",
            name=name,
            email=email
        )

    password_hash = generate_password_hash(password)
    user_id = create_user(name, email, password_hash)
    session['user_id'] = user_id
    return redirect(url_for('profile'))


@app.route("/login", methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('profile'))
    if request.method == 'GET':
        return render_template("login.html")

    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if not email or not password:
        return render_template("login.html", error="Email and password are required.")

    user = get_user_by_email(email)
    if user is None or not verify_password(user['password_hash'], password):
        return render_template("login.html", error="Invalid email or password.")

    session['user_id'] = user['id']
    return redirect(url_for('profile'))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('landing'))


@app.route("/profile")
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = get_user_by_id(user_id)

    if not user:
        session.clear()
        return redirect(url_for('login'))

    # Extract and validate date parameters
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')

    date_from = None
    date_to = None
    active_preset = 'all'

    # Both params must be present together or neither
    if date_from_str or date_to_str:
        if not (date_from_str and date_to_str):
            flash('Both start and end dates are required.', 'error')
        else:
            try:
                date_from_obj = datetime.strptime(date_from_str, '%Y-%m-%d').date()
                date_to_obj = datetime.strptime(date_to_str, '%Y-%m-%d').date()

                if date_from_obj > date_to_obj:
                    flash('Start date must be before end date.', 'error')
                else:
                    date_from = date_from_str
                    date_to = date_to_str
                    active_preset = detect_active_preset(date_from_obj, date_to_obj)
            except ValueError:
                pass  # Silently fall back to unfiltered

    # Query data with optional date filter
    stats = get_summary_stats(user_id, date_from, date_to)
    transactions = get_recent_transactions(user_id, limit=10, date_from=date_from, date_to=date_to)
    categories = get_category_breakdown(user_id, date_from, date_to)

    # Calculate preset dates for template
    today = date.today()
    presets = calculate_preset_dates(today)

    return render_template('profile.html', user=user, stats=stats,
                          transactions=transactions, categories=categories,
                          active_preset=active_preset, date_from=date_from,
                          date_to=date_to, presets=presets)


@app.route("/analytics")
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = get_user_by_id(user_id)

    if not user:
        session.clear()
        return redirect(url_for('login'))

    return render_template("analytics.html")


@app.route("/expenses/add", methods=['GET', 'POST'])
def add_expense():
    # Check if user is authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        today_date = date.today().strftime('%Y-%m-%d')
        return render_template('add_expense.html', today_date=today_date)

    # POST - process form submission
    user_id = session['user_id']

    # Validate CSRF token
    csrf_token = request.form.get('csrf_token', '')
    if not validate_csrf_token(csrf_token):
        return redirect(url_for('login'))

    # Get form data
    amount_str = request.form.get('amount', '').strip()
    category = request.form.get('category', '').strip()
    date_str = request.form.get('date', '').strip()
    description = request.form.get('description', '').strip() or None

    # Validate form
    amount, expense_date, errors = validate_expense_form(amount_str, category, date_str, VALID_CATEGORIES)

    # If there are validation errors, re-render the form
    if errors:
        return render_template('add_expense.html',
                                errors=errors,
                                amount=amount_str,
                                category=category,
                                date=date_str,
                                description=request.form.get('description', ''))

    # Insert the expense
    insert_expense(user_id, amount, category, date_str, description)

    flash('Expense added successfully.', 'success')
    return redirect(url_for('profile'))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    # Auth check
    if "user_id" not in session:
        return redirect(url_for("login"))

    # GET: Load and render form
    if request.method == "GET":
        expense = get_expense_by_id(id, session["user_id"])
        if not expense:
            abort(404)

        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=VALID_CATEGORIES
        )

    # POST: Validate and update
    # CSRF validation
    if not validate_csrf_token(request.form.get("csrf_token")):
        return redirect(url_for("login"))

    # Verify ownership before processing
    expense = get_expense_by_id(id, session["user_id"])
    if not expense:
        abort(404)

    # Extract form data
    amount_str = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_str = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip() or None

    # Validate form
    amount, parsed_date, errors = validate_expense_form(amount_str, category, date_str, VALID_CATEGORIES)

    # Re-render with errors if validation failed
    if errors:
        submitted_expense = {
            "id": id,
            "amount": amount_str,
            "category": category,
            "date": date_str,
            "description": description
        }
        return render_template(
            "edit_expense.html",
            expense=submitted_expense,
            categories=VALID_CATEGORIES,
            errors=errors
        )

    # Update database
    rows_updated = update_expense(id, session["user_id"], amount, category, date_str, description)
    if rows_updated == 0:
        abort(404)
    flash("Expense updated successfully!", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense_route(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if not expense:
        abort(404)

    delete_expense(id, session["user_id"])

    flash("Expense deleted successfully.", "success")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
