# Spendly

A lightweight personal expense tracker built with Flask and SQLite.

## Features

- User registration and authentication
- Track personal expenses
- View expense history
- Edit and delete expenses
- User profile management
- Clean, responsive UI

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Testing**: pytest

## Project Structure

```
spendly/
├── app.py              # Main application with all routes
├── database/
│   └── db.py           # SQLite helpers and database logic
├── templates/
│   ├── base.html       # Base template for all pages
│   └── *.html          # Page-specific templates
├── static/
│   ├── css/
│   │   ├── style.css       # Global styles
│   │   └── landing.css     # Landing page styles
│   └── js/
│       └── main.js         # Client-side JavaScript
├── tests/              # pytest test suite
├── requirements.txt    # Python dependencies
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd expense-tracker
```

2. Create and activate a virtual environment:
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to:
```
http://localhost:5001
```

## Running Tests

Run all tests:
```bash
pytest
```

Run a specific test file:
```bash
pytest tests/test_login.py
```

Run tests with verbose output:
```bash
pytest -v
```

Run tests and see print statements:
```bash
pytest -s
```

## Development

### Code Style

- Python code follows PEP 8 conventions
- Use snake_case for variables and functions
- Always use `url_for()` for internal links in templates
- Use parameterized queries for all database operations
- Keep route functions focused on a single responsibility

### Adding New Features

1. Routes go in `app.py`
2. Database logic goes in `database/db.py`
3. Create new templates extending `base.html`
4. Page-specific styles go in separate CSS files in `static/css/`
5. Write tests for new features in the `tests/` directory

## Deployment

The application is configured for deployment on Railway. See `railway.toml` for configuration details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests for new features
5. Ensure all tests pass
6. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues, questions, or contributions, please open an issue on the GitHub repository.
