#!/bin/bash
# run_tests.sh

# Navigate to the project root directory (aix_tool/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Define the working directory for generated artifacts
WORKING_DIR="$HOME/aix"

# Create the working directory if it doesn't exist
mkdir -p "$WORKING_DIR"

# Activate virtual environment
VENV_DIR="$HOME/aix_env"
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "Virtual environment not found at $VENV_DIR. Please run setup_env.sh first."
    exit 1
fi

# Ensure dependencies are installed, including autopep8
pip install requests gitpython pytest flask pandas github3.py psutil autopep8

# Ensure Node.js is installed for HTML/JS testing
node --version || brew install node
npm --version

# Ensure Julia is installed
julia --version || brew install julia

# Verify environment variables
echo $ANYTHINGLLM_API_KEY
echo $GITHUB_TOKEN

# Verify AnythingLLM workspace settings
curl -X GET "http://localhost:3001/api/v1/workspaces" -H "Authorization: Bearer CEBJPQP-0QG4NEF-JTM0KS2-T01XEPX"

# Test agent mode (optional, may fail if not configured)
curl -X POST "http://localhost:3001/api/v1/workspace/development/chat" -H "Authorization: Bearer CEBJPQP-0QG4NEF-JTM0KS2-T01XEPX" -H "Content-Type: application/json" -d '{"message": "Test message", "mode": "agent"}' || echo "Agent mode test failed, continuing..."

# Kill any existing http-server processes to avoid port conflicts
pkill -f "http-server" || echo "No existing http-server processes found."

# Start the HTTP server for HTML app in the background
npx http-server -p 8081 "$WORKING_DIR" &
sleep 2  # Wait for the server to start

# Run the script for HTML with debug logging
export PYTHON_LOG_LEVEL=DEBUG
PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT" python aix/main.py --language html --http-port 8081 --remote-url "https://github.com/nobulart/aix.git" "$@" 2>&1 | tee debug.log
if [ $? -ne 0 ]; then
    echo "HTML workflow failed. Exiting..."
    exit 1
fi

# Verify data.csv exists
cd "$WORKING_DIR"
if [ -f "data.csv" ]; then
    echo "data.csv found, proceeding with HTML app..."
else
    echo "data.csv not found. HTML app may not display data correctly."
fi

# Access the HTML app
open http://localhost:8081

# Run Jest tests for HTML if package.json exists
cd "$WORKING_DIR"
if [ -f "package.json" ]; then
    npm test
else
    echo "package.json not found. Skipping Jest tests for HTML."
fi

# Run the script for Python
cd "$PROJECT_ROOT"
PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT" python aix/main.py --language python --remote-url "https://github.com/nobulart/aix.git" "$@" 2>&1 | tee -a debug.log
if [ $? -ne 0 ]; then
    echo "Python workflow failed. Exiting..."
    exit 1
fi

# Kill any existing Flask processes
pkill -f "python.*app.py" || echo "No existing Flask processes found."

# Test the Python app in the background with a dynamic port
cd "$WORKING_DIR"
if [ -f "app.py" ]; then
    # Find a free port starting from 5000
    FLASK_PORT=5000
    while nc -z 127.0.0.1 $FLASK_PORT 2>/dev/null; do
        FLASK_PORT=$((FLASK_PORT + 1))
    done
    echo "Starting Flask app on port $FLASK_PORT..."
    # Modify app.py to accept a port argument if not already done
    grep -q "app.run(port=" app.py || sed -i '' 's/app.run()/app.run(port=int(os.getenv("FLASK_PORT", 5000)))/g' app.py
    grep -q "import os" app.py || sed -i '' '1i\
import os
' app.py
    export FLASK_PORT=$FLASK_PORT
    python app.py &
    sleep 2  # Wait for Flask to start
    curl http://localhost:$FLASK_PORT/hello
    curl http://localhost:$FLASK_PORT/data
else
    echo "app.py not found. Skipping Python app tests."
fi

# Run Python tests with PYTHONPATH set to include the aix directory
cd "$WORKING_DIR"
if [ -d "tests/python" ]; then
    PYTHONPATH="$PYTHONPATH:$WORKING_DIR" pytest tests/python --verbose
else
    echo "tests/python directory not found. Skipping Python tests."
fi

# Run the script for Julia
cd "$PROJECT_ROOT"
PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT" python aix/main.py --language julia --remote-url "https://github.com/nobulart/aix.git" "$@" 2>&1 | tee -a debug.log
if [ $? -ne 0 ]; then
    echo "Julia workflow failed. Exiting..."
    exit 1
fi

# Kill any existing Julia processes
pkill -f "julia --project" || echo "No existing Julia processes found."

# Test the Julia app in the background
cd "$WORKING_DIR"
if [ -f "app.jl" ]; then
    julia --project="$WORKING_DIR" -e 'using Pkg; Pkg.Registry.update(); Pkg.add(["Genie", "DataFrames", "CSV", "Test", "HTTP", "JSON3", "FilePaths"]); Pkg.instantiate()'
    julia --project="$WORKING_DIR" app.jl &
    sleep 15  # Increased sleep time to ensure the server starts
    # Retry curl commands up to 3 times with a 5-second delay
    for i in {1..3}; do
        curl http://localhost:8000/hello && break || sleep 5
    done
    for i in {1..3}; do
        curl http://localhost:8000/data && break || sleep 5
    done
else
    echo "app.jl not found. Skipping Julia app tests."
fi

# Run Julia tests
if [ -d "tests/julia" ]; then
    julia --project="$WORKING_DIR" -e 'cd("tests/julia"); include("test_app.jl")'
else
    echo "tests/julia directory not found. Skipping Julia tests."
fi

# Push to GitHub
cd "$WORKING_DIR"
if [ -d ".git" ]; then
    git push origin main
else
    echo "Not a Git repository. Skipping git push."
fi

# Unset debug logging
unset PYTHON_LOG_LEVEL

# Kill any remaining processes
pkill -f "http-server" || echo "No http-server processes to kill."
pkill -f "python.*app.py" || echo "No Flask processes to kill."
pkill -f "julia --project" || echo "No Julia processes to kill."

# Deactivate the virtual environment
deactivate