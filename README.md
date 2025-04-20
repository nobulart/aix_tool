# AIX Toolset

The AIX Toolset is a modular, model-agnostic Python-based automation framework for generating, testing, and deploying applications in HTML/JavaScript, Python, and Julia. It leverages the AnythingLLM API to generate code, integrates datasets, runs tests, generates documentation, sets up CI workflows, and manages version control via Git.

## Features

- **Code Generation**: Generates applications in HTML/JavaScript, Python (Flask), and Julia (Genie.jl) using the AnythingLLM API. Model selection is fully configurable.
- **Dataset Integration**: Downloads and integrates the Iris dataset for use in generated applications.
- **Testing**: Runs Jest tests for HTML, pytest for Python, and Julia tests for Genie.jl applications.
- **Documentation**: Generates a `README.md` with setup, running, and testing instructions for each application.
- **CI Setup**: Creates GitHub Actions workflows for continuous integration.
- **Version Control**: Initializes a Git repository and commits changes, with optional remote push to GitHub.

## Prerequisites

- **Python 3.9+**: Required to run the toolset.
- **Node.js 16+**: Required for HTML/JavaScript testing with Jest.
- **Julia 1.11+**: Required for Julia/Genie.jl applications.
- **AnythingLLM API**: Requires an API key set as `ANYTHINGLLM_API_KEY` environment variable.
- **GitHub Token**: Requires a token set as `GITHUB_TOKEN` for repository access (optional for forking/cloning).
- **LM Studio**: Used for model inference; ensure your desired models are loaded and compatible with AnythingLLM.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/nobulart/aix_tool.git
   cd aix_tool
   ```

2. Set up the virtual environment:

   ```bash
   bash scripts/setup_env.sh
   ```

3. Activate the virtual environment:

   ```bash
   source ~/aix_env/bin/activate
   ```

4. Set environment variables:

   ```bash
   export ANYTHINGLLM_API_KEY="your-anythingllm-api-key"
   export GITHUB_TOKEN="your-github-token"
   ```

## Usage

The toolset is executed via the `main.py` script, with options specified through command-line arguments. Two primary scripts are provided for convenience:

- `run_workflow.sh`: Runs the full workflow for a specified language.
- `run_tests.sh`: Runs the workflow and tests for all languages sequentially.

### Command-Line Options

| Option | Description | Default Value | Choices/Examples |
| --- | --- | --- | --- |
| `--code-model` | Model for code generation (overrides workspace default) | None | `my-code-model` |
| `--doc-model` | Model for documentation generation (overrides workspace default) | None | `my-doc-model` |
| `--chat-model` | Override the default chat model used by AnythingLLM | None | `my-chat-model` |
| `--agent-model` | Override the default agent model used by AnythingLLM | None | `my-agent-model` |
| `--api-base` | AnythingLLM API base URL | `http://localhost:3001` | `http://localhost:3001` |
| `--workspace` | Workspace slug for API requests | `development` | `development` |
| `--mode` | Chat mode for API requests | `chat` | `chat`, `agent` |
| `--language` | Programming language to generate code for | `python` | `python`, `julia`, `html` |
| `--fork-repo` | GitHub repository to fork (e.g., `user/repo`) | None | `nobulart/aix` |
| `--remote-url` | Git remote URL for pushing changes | `https://github.com/nobulart/aix.git` | `https://github.com/nobulart/aix.git` |
| `--http-port` | Port for the HTTP server (HTML apps) | `8081` | `8081` |

### Running the Workflow

Run the workflow for a specific language using `run_workflow.sh`:

```bash
bash scripts/run_workflow.sh --language python --chat-model my-chat-model --agent-model my-agent-model
```

### Running Tests for All Languages

Run the full workflow and tests for all languages using `run_tests.sh`:

```bash
bash scripts/run_tests.sh --chat-model my-chat-model --agent-model my-agent-model
```

### Example: Generating and Testing a Python Flask API

1. Run the workflow for Python:

   ```bash
   bash scripts/run_workflow.sh --language python --chat-model my-chat-model --agent-model my-agent-model
   ```

2. Expected Output:

   ```
   Running the workflow from /Users/craig/aix_tool...
   2025-04-21 00:05:56,524 - INFO - API endpoint is accessible at http://localhost:3001/api/docs
   2025-04-21 00:05:56,529 - INFO - Workspace 'development' is valid
   2025-04-21 00:05:56,529 - INFO - Workspace 'development' supports chatMode: chat, agentProvider: lmstudio
   2025-04-21 00:05:56,529 - INFO - Please ensure LM Studio has the desired models loaded or unloaded to manage RAM usage.
   2025-04-21 00:05:56,529 - INFO - If you need to unload models, do so in LM Studio UI (Model Manager > Unload All).
   Press Enter to continue once models are managed...
   2025-04-21 00:05:57,829 - INFO - Existing Git repository found at /Users/craig/aix
   2025-04-21 00:05:57,841 - INFO - Updated Git remote 'origin' to https://github.com/nobulart/aix.git
   2025-04-21 00:05:58,850 - INFO - Downloaded dataset to /Users/craig/aix/data.csv from https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data
   2025-04-21 00:05:58,851 - INFO - Sending request to AnythingLLM at http://localhost:3001/api/v1/workspace/development/chat with mode 'chat' and prompt: Write a Python script for a Flask REST API with a
   2025-04-21 00:06:06,452 - INFO - Response generated successfully
   2025-04-21 00:06:06,469 - INFO - Generated and saved /Users/craig/aix/app.py
   2025-04-21 00:06:06,469 - INFO - Sending request to AnythingLLM at http://localhost:3001/api/v1/workspace/development/chat with mode 'chat' and prompt: Write pytest tests for a Flask API defined in app.
   2025-04-21 00:06:15,273 - INFO - Response generated successfully
   2025-04-21 00:06:15,289 - INFO - Generated and saved /Users/craig/aix/tests/python/test_app.py
   2025-04-21 00:06:15,289 - INFO - Syntax check passed for /Users/craig/aix/tests/python/test_app.py
   2025-04-21 00:06:15,502 - INFO - Tests executed with exit code 2
   Test Results:
    ============================= test session starts ==============================
   platform darwin -- Python 3.13.3, pytest-8.3.5, pluggy-1.5.0 -- /Users/craig/aix_env/bin/python3.13
   cachedir: .pytest_cache
   rootdir: /Users/craig/aix
   collecting ... collected 0 items / 1 error
   
   ==================================== ERRORS ====================================
   __________________ ERROR collecting tests/python/test_app.py ___________________
   ImportError while importing test module '/Users/craig/aix/tests/python/test_app.py'.
   Hint: make sure your test modules/packages have valid Python names.
   Traceback:
   /opt/homebrew/Cellar/python@3.13/3.13.3/Frameworks/Python.framework/Versions/3.13/lib/python3.13/importlib/__init__.py:88: in import_module
       return _bootstrap._gcd_import(name[level:], package, level)
   tests/python/test_app.py:4: in <module>
       from ..app import app
   E   ImportError: attempted relative import beyond top-level package
   =========================== short test summary info ============================
   ERROR tests/python/test_app.py
   !!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
   =============================== 1 error in 0.09s ===============================
   
   2025-04-21 00:06:15,502 - INFO - Sending request to AnythingLLM at http://localhost:3001/api/v1/workspace/development/chat with mode 'chat' and prompt: Write a README.md file for a Flask API project wit
   2025-04-21 00:06:22,042 - INFO - Response generated successfully
   2025-04-21 00:06:22,048 - INFO - Generated and saved README.md
   2025-04-21 00:06:22,092 - INFO - Generated GitHub Actions workflow at /Users/craig/aix/.github/workflows/ci.yml
   2025-04-21 00:06:22,107 - INFO - Changes committed to repository
   Changes committed.
   ```

### Troubleshooting

- **Python Import Error**:

  - If Python tests fail with `ImportError: attempted relative import beyond top-level package`, ensure `/Users/craig/aix` is in the `PYTHONPATH`. Run tests manually to debug:

    ```bash
    cd /Users/craig/aix
    PYTHONPATH="$PYTHONPATH:/Users/craig/aix" pytest tests/python --verbose
    ```

- **Flask Port Conflict**:

  - If Flask fails to start due to a port conflict, identify the process using the port:

    ```bash
    lsof -i :5000
    kill -9 <pid>
    ```

- **Git Push Failure**:

  - If `git push` fails, verify the repository exists and you have push access:

    ```bash
    git ls-remote https://github.com/nobulart/aix.git
    ```

  - Create the repository on GitHub if it doesn’t exist.

## Contributing

Contributions are welcome! Please fork the repository, make your changes, and submit a pull request.

## License

This project is licensed under the MIT License.