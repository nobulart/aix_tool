#!/bin/bash
# run_workflow.sh

# Define the virtual environment directory
VENV_DIR="$HOME/aix_env"

# Activate the virtual environment
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "Virtual environment not found at $VENV_DIR. Please run setup_env.sh first."
    exit 1
fi

# Navigate to the project root directory (aix_tool/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Run the main workflow with PYTHONPATH set
echo "Running the workflow from $PROJECT_ROOT..."
PYTHONPATH="$PYTHONPATH:$PROJECT_ROOT" python aix/main.py --remote-url "https://github.com/nobulart/aix.git" "$@"

# Deactivate the virtual environment
deactivate