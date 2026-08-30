import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
from database.db import init_db, seed_db, get_user_by_email, create_user, verify_password
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

with app.app_context():
    init_db()
    seed_db()


@app.context_processor
def inject_user():
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            return {'current_user': {'name': user['name']}}
    return {}


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


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
