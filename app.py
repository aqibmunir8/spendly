import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash
from database.db import init_db, seed_db, get_user_by_email, create_user, verify_password

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

with app.app_context():
    init_db()
    seed_db()


@app.context_processor
def inject_user():
    if 'user_id' in session:
        return {'current_user': {'name': 'Nitish Kumar'}}
    return {}


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

    user = {
        'name': 'Nitish Kumar',
        'email': 'nitish@example.com',
        'initials': 'NK',
        'member_since': 'August 2026'
    }

    stats = {
        'total_spent': 409.85,
        'transaction_count': 8,
        'top_category': 'Health'
    }

    transactions = [
        {'date': '2026-08-22', 'description': 'Lunch at cafe', 'category': 'Food', 'amount': 18.75},
        {'date': '2026-08-20', 'description': 'Birthday gift', 'category': 'Other', 'amount': 25.50},
        {'date': '2026-08-18', 'description': 'New running shoes', 'category': 'Shopping', 'amount': 67.80},
        {'date': '2026-08-15', 'description': 'Movie tickets', 'category': 'Entertainment', 'amount': 35.00},
        {'date': '2026-08-12', 'description': 'Doctor appointment', 'category': 'Health', 'amount': 120.00}
    ]

    categories = [
        {'name': 'Health', 'total': 120.00, 'percentage': 29},
        {'name': 'Bills', 'total': 85.30, 'percentage': 21},
        {'name': 'Shopping', 'total': 67.80, 'percentage': 17},
        {'name': 'Food', 'total': 64.25, 'percentage': 16},
        {'name': 'Entertainment', 'total': 35.00, 'percentage': 9},
        {'name': 'Other', 'total': 25.50, 'percentage': 6},
        {'name': 'Transport', 'total': 12.00, 'percentage': 3}
    ]

    return render_template('profile.html', user=user, stats=stats,
                          transactions=transactions, categories=categories)


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
