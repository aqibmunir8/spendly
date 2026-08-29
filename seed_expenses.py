import sqlite3
import random
from datetime import datetime, timedelta
from database.db import get_db

# Configuration
USER_ID = 3
COUNT = 10
MONTHS = 12

# Category definitions with realistic Indian amounts and descriptions
CATEGORIES = {
    'Food': {
        'weight': 30,
        'amount_range': (50, 800),
        'descriptions': [
            'Grocery shopping at Big Bazaar',
            'Lunch at office cafeteria',
            'Dinner at local restaurant',
            'Breakfast at cafe',
            'Weekly vegetables from market',
            'Swiggy food delivery',
            'Zomato order',
            'Tea and snacks',
            'Monthly ration',
            'Fast food at McDonald\'s'
        ]
    },
    'Transport': {
        'weight': 25,
        'amount_range': (20, 500),
        'descriptions': [
            'Uber ride to office',
            'Ola auto booking',
            'Metro card recharge',
            'Petrol refill',
            'Bus pass monthly',
            'Rapido bike ride',
            'Parking charges',
            'Toll charges',
            'Auto rickshaw fare',
            'Railway ticket booking'
        ]
    },
    'Bills': {
        'weight': 15,
        'amount_range': (200, 3000),
        'descriptions': [
            'Electricity bill payment',
            'Broadband internet bill',
            'Mobile recharge',
            'Water bill',
            'Gas cylinder refill',
            'DTH TV recharge',
            'Society maintenance',
            'Credit card payment',
            'Rent payment',
            'Loan EMI'
        ]
    },
    'Health': {
        'weight': 10,
        'amount_range': (100, 2000),
        'descriptions': [
            'Doctor consultation',
            'Pharmacy medicines',
            'Health insurance premium',
            'Gym membership',
            'Dental checkup',
            'Lab tests',
            'Eye checkup',
            'Physiotherapy session',
            'Vitamins and supplements',
            'Hospital visit'
        ]
    },
    'Entertainment': {
        'weight': 10,
        'amount_range': (100, 1500),
        'descriptions': [
            'Netflix subscription',
            'Movie tickets at PVR',
            'Amazon Prime renewal',
            'Concert tickets',
            'Gaming subscription',
            'Book purchase from Amazon',
            'Spotify premium',
            'Weekend outing',
            'Theme park entry',
            'Cricket match tickets'
        ]
    },
    'Shopping': {
        'weight': 15,
        'amount_range': (200, 5000),
        'descriptions': [
            'Clothes from Myntra',
            'Shoes purchase',
            'Electronics from Flipkart',
            'Amazon shopping',
            'Mobile accessories',
            'Home decor items',
            'Kitchen appliances',
            'Laptop purchase',
            'Watch from brand store',
            'Furniture shopping'
        ]
    },
    'Other': {
        'weight': 10,
        'amount_range': (50, 1000),
        'descriptions': [
            'Birthday gift',
            'Charity donation',
            'Pet supplies',
            'Stationery items',
            'Haircut and grooming',
            'Laundry services',
            'Photography session',
            'Home repairs',
            'Courier charges',
            'Miscellaneous expense'
        ]
    }
}

def verify_user_exists(user_id):
    """Check if user exists in database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE id = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def generate_expenses(user_id, count, months):
    """Generate random expenses for a user."""
    today = datetime.now().date()
    start_date = today - timedelta(days=months * 30)

    # Create weighted category list
    weighted_categories = []
    for category, config in CATEGORIES.items():
        weighted_categories.extend([category] * config['weight'])

    expenses = []
    for _ in range(count):
        # Random category selection based on weights
        category = random.choice(weighted_categories)
        config = CATEGORIES[category]

        # Random amount within category range
        amount = round(random.uniform(*config['amount_range']), 2)

        # Random date within the time range
        days_ago = random.randint(0, months * 30)
        expense_date = today - timedelta(days=days_ago)

        # Random description from category
        description = random.choice(config['descriptions'])

        expenses.append({
            'user_id': user_id,
            'amount': amount,
            'category': category,
            'date': expense_date.strftime('%Y-%m-%d'),
            'description': description
        })

    # Sort by date for better readability
    expenses.sort(key=lambda x: x['date'])

    return expenses

def insert_expenses(expenses):
    """Insert expenses into database using a transaction."""
    conn = get_db()
    cursor = conn.cursor()

    try:
        for expense in expenses:
            cursor.execute(
                'INSERT INTO expenses (user_id, amount, category, date, description) '
                'VALUES (?, ?, ?, ?, ?)',
                (expense['user_id'], expense['amount'], expense['category'],
                 expense['date'], expense['description'])
            )

        conn.commit()
        print(f"[SUCCESS] Successfully inserted {len(expenses)} expenses")
        return True
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error inserting expenses: {e}")
        return False
    finally:
        conn.close()

def main():
    print(f"Seeding {COUNT} expenses for user {USER_ID} across {MONTHS} months...")
    print()

    # Step 1: Verify user exists
    if not verify_user_exists(USER_ID):
        print(f"[ERROR] No user found with id {USER_ID}.")
        return

    print(f"[OK] User {USER_ID} verified")
    print()

    # Step 2: Generate expenses
    expenses = generate_expenses(USER_ID, COUNT, MONTHS)

    # Step 3: Insert expenses
    if insert_expenses(expenses):
        # Step 4: Display summary
        date_range = f"{expenses[0]['date']} to {expenses[-1]['date']}"
        print(f"Date range: {date_range}")
        print()
        print("Sample of inserted expenses:")
        print()

        sample = expenses[:5] if len(expenses) >= 5 else expenses
        for i, exp in enumerate(sample, 1):
            print(f"{i}. {exp['date']} | {exp['category']:<15} | Rs.{exp['amount']:>8.2f} | {exp['description']}")

if __name__ == '__main__':
    main()
