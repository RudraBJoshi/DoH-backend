#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Starting MalwareMadness backend..."

# Create venv + install deps if missing
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Installing dependencies..."
    venv/bin/pip install --quiet Flask Flask-Login Flask-SQLAlchemy Flask-Migrate \
        Flask-RESTful Flask-Cors PyJWT python-dotenv Werkzeug requests pymysql
    echo "Done."
fi

source venv/bin/activate
echo "Backend running at http://localhost:8800"
echo ""
python main.py

