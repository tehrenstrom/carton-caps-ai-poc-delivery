#!/bin/bash
set -e  # Exit on error

echo "🚀 Setting up Carton Caps API development environment..."

# Check for Python installation
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "🌱 Creating Python virtual environment..."
    python3 -m venv .venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "Dependencies installed."

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file with sample values..."
    cat > .env << EOL
# Database configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cartoncaps

# Google API Key for Gemini LLM
GOOGLE_API_KEY=your_api_key_here

# Debug settings
DEBUG=True
EOL
    echo ".env file created. Please update the values with your actual credentials."
else
    echo ".env file already exists."
fi

# Check if PostgreSQL is running
echo "Checking PostgreSQL connection..."
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 -U postgres &> /dev/null; then
        echo "PostgreSQL is running."
    else
        echo "PostgreSQL is not running or not accessible with default settings."
        echo "Make sure your PostgreSQL server is running and update the DATABASE_URL in .env if needed."
    fi
else
    echo "pg_isready not found. Cannot check PostgreSQL connection."
    echo "Make sure your PostgreSQL server is running and update the DATABASE_URL in .env if needed."
fi

echo "Next steps:"
echo "1. Update your .env file with actual credentials"
echo "2. Run 'python scripts/seed_database.py' to initialize database with sample data"
echo "3. Run 'uvicorn app.main:app --reload' to start the development server"
echo "Setup complete! Happy coding!" 