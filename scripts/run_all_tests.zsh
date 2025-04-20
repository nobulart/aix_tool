#!/bin/zsh
# Navigate to the correct directory
cd ~/flowtest

# Activate virtual environment
source ~/flowtest_env/bin/activate

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
curl -X POST "http://localhost:3001/api/v1/workspace/development/chat" -H "Authorization: Bearer CEBJPQP-0QG4NEF-JTM0KS2-T01XEPX" -H "Content-Type: application/json" -d '{"message": "Test message", "mode": "agent", "model": "llama-3-groq-8b-tool-use"}' || echo "Agent mode test failed, continuing..."

# Kill any existing http-server processes to avoid port conflicts
pkill -f "http-server" || echo "No existing http-server processes found."

# Start the HTTP server for HTML app in the background
npx http-server -p 8081 &
sleep 2  # Wait for the server to start

# Run the script for HTML with debug logging
export PYTHON_LOG_LEVEL=DEBUG
python flowtest.py --language html --code-model llama-3-groq-8b-tool-use --http-port 8081 --remote-url "https://github.com/nobulart/flowtest.git" 2>&1 | tee debug.log

# Verify data.csv exists
if [ -f "data.csv" ]; then
    echo "data.csv found, proceeding with HTML app..."
else
    echo "data.csv not found. HTML app may not display data correctly."
fi

# Access the HTML app
open http://localhost:8081

# Run Jest tests for HTML
npm test

# Run the script for Python
python flowtest.py --language python --code-model llama-3-groq-8b-tool-use --remote-url "https://github.com/nobulart/flowtest.git" 2>&1 | tee -a debug.log

# Kill any existing Flask processes
pkill -f "python app.py" || echo "No existing Flask processes found."

# Test the Python app in the background with a different port to avoid conflicts
FLASK_PORT=5001
python app.py --port $FLASK_PORT &
sleep 2  # Wait for Flask to start
curl http://localhost:$FLASK_PORT/hello
curl http://localhost:$FLASK_PORT/data

# Run Python tests with PYTHONPATH set to include the flowtest directory
export PYTHONPATH=$PYTHONPATH:~/flowtest
cd ~/flowtest
pytest tests/python --verbose

# Run the script for Julia
python flowtest.py --language julia --code-model llama-3-groq-8b-tool-use --remote-url "https://github.com/nobulart/flowtest.git" 2>&1 | tee -a debug.log

# Kill any existing Julia processes
pkill -f "julia --project" || echo "No existing Julia processes found."

# Test the Julia app in the background
julia --project=~/flowtest -e 'using Pkg; Pkg.Registry.update(); Pkg.add(["Genie", "DataFrames", "CSV", "Test", "HTTP", "JSON3", "FilePaths"]); Pkg.instantiate()'
julia --project=~/flowtest app.jl &
sleep 5  # Wait for the server to start
curl http://localhost:8000/hello
curl http://localhost:8000/data

# Run Julia tests
julia --project=~/flowtest -e 'cd("tests/julia"); include("test_app.jl")'

# Push to GitHub
git push origin main

# Unset debug logging
unset PYTHON_LOG_LEVEL

# Kill any remaining processes
pkill -f "http-server" || echo "No http-server processes to kill."
pkill -f "python app.py" || echo "No Flask processes to kill."
pkill -f "julia --project" || echo "No Julia processes to kill."