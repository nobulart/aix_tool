# Note: Store API key and GitHub token in environment variables for security
# Set via:
#   export ANYTHINGLLM_API_KEY="CEBJPQP-0QG4NEF-JTM0KS2-T01XEPX"
#   export GITHUB_TOKEN="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"
# Run in a virtual environment:
#   /opt/homebrew/bin/python3 -m venv flowtest_env
#   source flowtest_env/bin/activate
#   pip install requests gitpython pytest flask pandas github3.py psutil autopep8

import requests
import git
import subprocess
import os
import argparse
import sys
import logging
import json
import ast
import re
import github3
import pandas as pd
import urllib.request
from pathlib import Path
import time
import urllib.error
import uuid
import shutil
import psutil
import textwrap
import autopep8

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REPO_PATH = os.path.expanduser("~/flowtest")
LM_STUDIO_API = "http://localhost:1234"

def check_api_availability(api_base, workspace, api_key):
    """Verify API endpoint and workspace accessibility."""
    try:
        response = requests.get(f"{api_base}/api/docs", timeout=5)
        response.raise_for_status()
        logger.info("API endpoint is accessible at %s/api/docs", api_base)

        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(f"{api_base}/api/v1/workspaces", headers=headers)
        response.raise_for_status()
        workspaces = response.json().get("workspaces", [])
        workspace_slugs = [ws["slug"] for ws in workspaces]
        if workspace not in workspace_slugs:
            logger.error("Workspace '%s' not found. Available workspaces: %s", workspace, workspace_slugs)
            return False, None
        logger.info("Workspace '%s' is valid", workspace)

        for ws in workspaces:
            if ws["slug"] == workspace:
                chat_mode = ws.get("chatMode", "chat")
                agent_provider = ws.get("agentProvider")
                chat_model = ws.get("chatModel")
                agent_model = ws.get("agentModel")
                logger.info("Workspace '%s' supports chatMode: %s, agentProvider: %s, chatModel: %s, agentModel: %s",
                            workspace, chat_mode, agent_provider, chat_model, agent_model)
                return True, {"chat_model": chat_model, "agent_model": agent_model, "agent_provider": agent_provider}
        return False, None
    except requests.exceptions.RequestException as e:
        logger.error("API or workspace not accessible at %s: %s", api_base, e)
        return False, None

def check_ram_usage():
    """Check current RAM usage and warn if exceeding threshold."""
    ram = psutil.virtual_memory()
    used_ram = ram.used / (1024 ** 3)  # Convert to GB
    total_ram = ram.total / (1024 ** 3)
    threshold = 50  # 50 GB threshold for a 64 GB system
    if used_ram > threshold:
        logger.warning("High RAM usage detected: %.2f GB used out of %.2f GB. Consider closing other applications.", used_ram, total_ram)
    return used_ram < threshold

def initial_model_check():
    """Prompt user to ensure LM Studio models are managed before starting."""
    logger.info("Please ensure LM Studio has the desired models loaded or unloaded to manage RAM usage.")
    logger.info("If you need to unload models, do so in LM Studio UI (Model Manager > Unload All).")
    input("Press Enter to continue once models are managed...")

def clean_code_output(text, language):
    """Clean LLM output to extract raw code, removing markdown and invalid content."""
    # Remove markdown code fences
    code = re.sub(r'```(?:python|julia|html|javascript)?\n([\s\S]*?)\n```', r'\1', text, flags=re.MULTILINE)
    code = re.sub(r'```[\s\S]*', '', code)
    code = code.strip()
    # Remove explanatory text, headers, or non-code lines
    lines = code.splitlines()
    code_lines = []
    for line in lines:
        line = line.rstrip()
        if not line:  # Skip empty lines
            continue
        if line.startswith(('# ', '##', '###', '*', '-')) or line.lower().startswith(('example', 'note', 'output', 'certainly', 'below', 'here')):
            continue
        stripped_line = line.lstrip()
        if not stripped_line:
            continue
        code_lines.append(line)
    return '\n'.join(code_lines).strip()

def format_python_code(code):
    """Format Python code using autopep8 to fix indentation and style issues."""
    try:
        formatted_code = autopep8.fix_code(code, options={'aggressive': 2})
        return formatted_code.strip()
    except Exception as e:
        logger.error("Failed to format Python code with autopep8: %s", e)
        return code  # Return unformatted code as a fallback

def validate_code_file(file_path, language):
    """Check if a code file has valid syntax."""
    try:
        with open(file_path, "r") as f:
            code = f.read()
        logger.debug("File contents for %s:\n%s", file_path, code)
        if language == "python":
            ast.parse(code)
        elif language == "javascript":
            if not code.strip():
                raise ValueError("Empty JavaScript code")
        elif language == "julia":
            if not code.strip():
                raise ValueError("Empty Julia code")
        logger.info("Syntax check passed for %s", file_path)
        return True
    except (SyntaxError, ValueError) as e:
        logger.error("Syntax error in %s: %s", file_path, e)
        return False
    except Exception as e:
        logger.error("Error validating %s: %s", file_path, e)
        return False

def init_repo(github_token, fork_repo=None, remote_url=None):
    """Initialize a Git repository, optionally forking a GitHub repo and setting remote."""
    try:
        if not os.path.exists(REPO_PATH):
            os.makedirs(REPO_PATH)
            repo = git.Repo.init(REPO_PATH)
            with open(f"{REPO_PATH}/README.md", "w") as f:
                f.write("# Project\n")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")
            logger.info("Initialized Git repository at %s", REPO_PATH)
        else:
            repo = git.Repo(REPO_PATH)

        # Ensure the branch is 'main'
        if repo.active_branch.name == "master":
            repo.git.checkout("-b", "main")
            logger.info("Renamed branch from 'master' to 'main'")
        elif repo.active_branch.name != "main":
            repo.git.checkout("main")

        # Create __init__.py for Python package structure
        init_file = os.path.join(REPO_PATH, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("")
            repo.index.add(["__init__.py"])
            repo.index.commit("Add __init__.py for package structure")

        # Set up remote if provided
        if remote_url:
            try:
                if "origin" in repo.remotes:
                    repo.remotes.origin.set_url(remote_url)
                    logger.info("Updated Git remote 'origin' to %s", remote_url)
                else:
                    repo.create_remote("origin", remote_url)
                    logger.info("Set Git remote 'origin' to %s", remote_url)
            except Exception as e:
                logger.warning("Failed to set Git remote: %s", e)
                logger.info("Please set the remote manually with: git remote add origin <your-repo-url>")

        # Fork and clone a GitHub repository if specified
        if fork_repo and github_token:
            gh = github3.login(token=github_token)
            repo_parts = fork_repo.split("/")
            if len(repo_parts) != 2:
                raise ValueError("Invalid repository format. Use 'user/repo'")
            owner, repo_name = repo_parts
            source_repo = gh.repository(owner, repo_name)
            if not source_repo:
                raise ValueError(f"Repository {fork_repo} not found")
            forked_repo = source_repo.create_fork()
            logger.info("Forked repository %s to %s", fork_repo, forked_repo.full_name)
            clone_path = os.path.join(REPO_PATH, repo_name)
            if os.path.exists(clone_path):
                logger.warning("Directory %s already exists. Skipping clone.", clone_path)
            else:
                git.Repo.clone_from(forked_repo.clone_url, clone_path)
                logger.info("Cloned forked repository to %s", clone_path)

        return repo
    except Exception as e:
        logger.error("Failed to initialize repository: %s", e)
        raise

def download_dataset(dataset_urls, output_path, retries=3, delay=2):
    """Download a public dataset with retries and fallback URLs."""
    for url in dataset_urls:
        for attempt in range(retries):
            try:
                urllib.request.urlretrieve(url, output_path)
                logger.info("Downloaded dataset to %s from %s", output_path, url)
                return True
            except urllib.error.HTTPError as e:
                logger.warning("Attempt %d/%d failed to download dataset from %s: %s", attempt + 1, retries, url, e)
                if attempt < retries - 1:
                    time.sleep(delay)
            except Exception as e:
                logger.error("Failed to download dataset from %s: %s", url, e)
                break
    logger.warning("All dataset download attempts failed. Continuing without dataset.")
    return False

def query_anythingllm(prompt, api_base, workspace, api_key, mode="chat", model=None, workspace_config=None):
    """Query AnythingLLM for a response and return text and model used."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "message": prompt,
            "mode": mode
        }
        if model:
            payload["model"] = model
        url = f"{api_base}/api/v1/workspace/{workspace}/chat"
        logger.info("Sending request to AnythingLLM at %s with mode '%s' and prompt: %s", url, mode, prompt[:50])
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        
        logger.debug("Full API response: %s", json.dumps(response_data, indent=2))
        
        if "error" in response_data and response_data["error"]:
            error_msg = response_data["error"]
            logger.error("API returned error: %s", error_msg)
            raise ValueError(f"API error: {error_msg}")
        if "textResponse" not in response_data or response_data["textResponse"] is None:
            logger.error("No valid 'textResponse' in response: %s", response_data)
            raise ValueError("No valid response from AnythingLLM")
        
        model_used = response_data.get("metrics", {}).get("model")
        if not model_used:
            model_used = response_data.get("chatModel")
        if not model_used and workspace_config:
            model_used = workspace_config.get("agent_model" if mode == "agent" else "chat_model")
        if not model_used:
            model_used = model or "unknown"
        logger.info("Response generated by model: %s", model_used)
        
        return response_data["textResponse"], model_used
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP error from AnythingLLM: %s, Response text: %s", e, response.text)
        raise
    except requests.exceptions.JSONDecodeError as e:
        logger.error("Failed to parse JSON response: %s, Response text: %s", e, response.text)
        raise
    except Exception as e:
        logger.error("Unexpected error querying AnythingLLM: %s", e)
        raise

def generate_code(prompt, api_base, workspace, api_key, mode, language, model=None, workspace_config=None):
    """Generate code using AnythingLLM with fallback, and format Python code with autopep8."""
    try:
        if model and not check_ram_usage():
            logger.warning("Skipping model-specific operations due to high RAM usage.")
            model = None
        text, model_used = query_anythingllm(prompt, api_base, workspace, api_key, mode, model, workspace_config)
        cleaned_text = clean_code_output(text, language)
        # Format Python code with autopep8 to fix indentation
        if language == "python":
            cleaned_text = format_python_code(cleaned_text)
        return cleaned_text, model_used
    except Exception as e:
        logger.error("Failed to generate code: %s", e)
        raise

def run_tests(language, http_port=8081):
    """Run tests based on language."""
    try:
        test_dir = f"{REPO_PATH}/tests/{language}"
        if language == "html":
            test_file = f"{test_dir}/test_index.test.js"
        elif language == "python":
            test_file = f"{test_dir}/test_app.py"
        else:  # julia
            test_file = f"{test_dir}/test_app.jl"
        if not os.path.exists(test_file):
            logger.error("Test file %s does not exist", test_file)
            return "No test file found"
        
        if not validate_code_file(test_file, "javascript" if language == "html" else language):
            logger.error("Skipping tests due to invalid test file")
            return "Invalid test file syntax"
        
        with open(test_file, "r") as f:
            logger.debug("Test file contents:\n%s", f.read())
        
        env = os.environ.copy()
        if language == "python":
            # Ensure PYTHONPATH includes the REPO_PATH (/Users/craig/flowtest) to allow relative imports
            env["PYTHONPATH"] = f"{REPO_PATH}:{env.get('PYTHONPATH', '')}"
            # Run pytest from the REPO_PATH to ensure the test directory is recognized as a package
            result = subprocess.run(
                ["pytest", f"tests/{language}", "--verbose"],
                cwd=REPO_PATH,
                capture_output=True,
                text=True,
                env=env
            )
        elif language == "html":
            # Setup for Jest testing
            package_json_path = os.path.join(REPO_PATH, "package.json")
            if not os.path.exists(package_json_path):
                package_json_content = '''
                {
                  "name": "flowtest",
                  "version": "1.0.0",
                  "scripts": {
                    "test": "jest --testPathPattern=tests/html"
                  },
                  "devDependencies": {
                    "jest": "^29.7.0",
                    "jest-environment-jsdom": "^29.7.0"
                  },
                  "jest": {
                    "testMatch": ["**/tests/html/*.test.js"],
                    "testEnvironment": "jsdom"
                  }
                }
                '''
                with open(package_json_path, "w") as f:
                    f.write(package_json_content.strip())
            # Ensure dependencies are installed
            try:
                subprocess.run(["npm", "install", "jest@29.7.0", "jest-environment-jsdom@29.7.0"], cwd=REPO_PATH, check=True)
            except subprocess.CalledProcessError as e:
                logger.warning("Initial npm install failed: %s", e)
                # Fallback: Clean install
                subprocess.run(["npm", "install"], cwd=REPO_PATH, check=True)
            # Verify installation
            result = subprocess.run(["npm", "list", "jest", "jest-environment-jsdom"], cwd=REPO_PATH, capture_output=True, text=True)
            logger.info("npm list jest jest-environment-jsdom:\n%s", result.stdout)
            if "jest@29.7.0" not in result.stdout or "jest-environment-jsdom@29.7.0" not in result.stdout:
                logger.error("Failed to install jest or jest-environment-jsdom. Please install manually with: npm install jest@29.7.0 jest-environment-jsdom@29.7.0")
                return "Jest dependencies not installed"
            # Verify HTML output by fetching data.csv directly
            try:
                data_csv_url = f"http://localhost:{http_port}/data.csv"
                response = requests.get(data_csv_url, timeout=5)
                response.raise_for_status()
                if "Iris-setosa" in response.text:
                    logger.info("HTML output verified: Iris dataset found in data.csv.")
                else:
                    logger.error("HTML output verification failed: Iris dataset not found in data.csv.")
                    logger.debug("data.csv content: %s", response.text)
            except requests.exceptions.RequestException as e:
                logger.error("Failed to fetch data.csv for HTML verification: %s", e)
            result = subprocess.run(
                ["npm", "test"],
                cwd=REPO_PATH,
                capture_output=True,
                text=True
            )
        else:  # julia
            # Update registry and install dependencies
            subprocess.run(
                ["julia", "--project=.", "-e", 'using Pkg; Pkg.Registry.update(); Pkg.add(["Genie", "DataFrames", "CSV", "Test", "HTTP", "JSON3", "FilePaths"]); Pkg.instantiate()'],
                cwd=REPO_PATH,
                check=True
            )
            # Run tests directly on the project
            result = subprocess.run(
                ["julia", "--project=.", "-e", f'cd("{test_dir}"); include("test_app.jl")'],
                cwd=REPO_PATH,
                capture_output=True,
                text=True
            )
        logger.info("Tests executed with exit code %s", result.returncode)
        return result.stdout + (result.stderr or "")
    except subprocess.CalledProcessError as e:
        logger.error("Tests failed with exit code %s: %s", e.returncode, e.stderr)
        return (e.stdout or "") + (e.stderr or "")
    except Exception as e:
        logger.error("Unexpected error running tests: %s", e)
        return str(e)

def generate_github_actions_workflow(repo, language):
    """Generate a GitHub Actions workflow for CI."""
    if language == "html":
        workflow_content = """
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '16'
    - name: Install dependencies
      run: npm install
    - name: Run tests
      run: npm test
"""
    else:
        workflow_content = f"""
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up {language.capitalize()}
      uses: {'julia-actions/setup-julia@v1' if language == 'julia' else 'actions/setup-python@v4'}
      with:
        {'version: "1.11"' if language == 'julia' else 'python-version: "3.13"'}
    - name: Install dependencies
      run: |
        {'julia --project=. -e "using Pkg; Pkg.instantiate()"' if language == 'julia' else 'pip install -r requirements.txt'}
    - name: Run tests
      run: |
        {'julia --project=. -e "cd(\\"tests/julia\\"); include(\\\"test_app.jl\\")"' if language == 'julia' else 'pytest tests/python --verbose'}
"""
    workflow_path = os.path.join(REPO_PATH, ".github/workflows/ci.yml")
    os.makedirs(os.path.dirname(workflow_path), exist_ok=True)
    with open(workflow_path, "w") as f:
        f.write(workflow_content.strip())
    repo.index.add([".github/workflows/ci.yml"])
    repo.index.commit("Add GitHub Actions CI workflow")
    logger.info("Generated GitHub Actions workflow at %s", workflow_path)

def main():
    parser = argparse.ArgumentParser(description="Agentic workflow for code generation, testing, and dataset integration")
    parser.add_argument("--code-model", help="Model for code generation (default: workspace default)")
    parser.add_argument("--doc-model", help="Model for documentation generation (default: workspace default)")
    parser.add_argument("--api-base", default="http://localhost:3001", help="AnythingLLM API base URL")
    parser.add_argument("--workspace", default="development", help="Workspace slug for API requests")
    parser.add_argument("--mode", default="chat", choices=["chat", "agent"], help="Chat mode (chat or agent)")
    parser.add_argument("--language", default="python", choices=["python", "julia", "html"], help="Programming language (python, julia, or html)")
    parser.add_argument("--fork-repo", help="GitHub repository to fork (e.g., user/repo)")
    parser.add_argument("--remote-url", default="https://github.com/nobulart/flowtest.git", help="Git remote URL for pushing changes")
    parser.add_argument("--http-port", default="8081", type=int, help="Port for the HTTP server (default: 8081)")
    args = parser.parse_args()

    # Ensure working directory is consistent
    os.chdir(REPO_PATH)

    # Load API key and GitHub token
    api_key = os.getenv("ANYTHINGLLM_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    if not api_key:
        logger.error("ANYTHINGLLM_API_KEY environment variable not set")
        sys.exit(1)

    # Check API and workspace
    is_available, workspace_config = check_api_availability(args.api_base, args.workspace, api_key)
    if not is_available:
        logger.error("Aborting due to inaccessible API or invalid workspace")
        sys.exit(1)

    if args.mode == "agent" and (not workspace_config or not workspace_config.get("agent_provider")):
        logger.warning("Agent mode selected but no agent provider configured. Falling back to chat mode.")
        args.mode = "chat"

    try:
        # Initial model check
        initial_model_check()

        # Initialize repo
        repo = init_repo(github_token, args.fork_repo, args.remote_url)
        
        # Download dataset (Iris dataset with fallback) for Python and HTML
        if args.language in ["python", "html"]:
            dataset_urls = [
                "https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data",
                "https://raw.githubusercontent.com/pandas-dev/pandas/main/pandas/tests/io/data/csv/iris.csv"
            ]
            dataset_path = os.path.join(REPO_PATH, "data.csv")
            dataset_success = download_dataset(dataset_urls, dataset_path)
            if not dataset_success:
                logger.error("Failed to download dataset. HTML and Python apps may not function correctly.")
            elif not os.path.exists(dataset_path):
                logger.error("Dataset file %s does not exist after download attempt.", dataset_path)
                dataset_success = False
        else:
            dataset_success = True  # Julia will handle dataset separately if needed

        # Generate code
        if args.language == "python":
            code_prompt = (
                "Write a Python script for a Flask REST API with a single /hello endpoint that returns 'Hello, World!' as JSON, "
                "and a /data endpoint that reads data.csv (an Iris dataset) using pandas and returns the first 5 rows as JSON. "
                "If data.csv is missing, return {'error': 'Dataset not found'}. "
                "Use Flask's jsonify and ensure the app can be run with `app.run()`. Ensure proper indentation for all code blocks with 4 spaces per level. "
                "Output only the Python code, no markdown, code fences, or explanatory text. "
                "Example:\nfrom flask import Flask, jsonify\nimport pandas as pd\nfrom pathlib import Path\napp = Flask(__name__)\n@app.route('/hello')\ndef hello():\n    return jsonify({'message': 'Hello, World!'})\n@app.route('/data')\ndef data():\n    if Path('data.csv').exists():\n        df = pd.read_csv('data.csv')\n        return jsonify(df.head().to_dict())\n    return jsonify({'error': 'Dataset not found'})\nif __name__ == '__main__':\n    app.run()"
            )
        elif args.language == "html":
            code_prompt = (
                "Write an HTML file with CSS and JS for a webpage displaying the Iris dataset from a file named 'data.csv' in a table. "
                "Use fetch to load the CSV strictly from 'data.csv' (do not use 'iris.csv' or any other filename). "
                "Add error handling to log fetch errors to the console and display 'Error: Unable to load data' in the table if the fetch fails. "
                "The Iris dataset has 5 columns: sepal length, sepal width, petal length, petal width, and species. "
                "Create a table with headers for these columns and populate the rows with the CSV data. Handle empty or malformed rows by skipping them. "
                "Output only the HTML code, no markdown, code fences, or explanatory text. "
                "Example:\n<!DOCTYPE html>\n<html>\n<head>\n<style>\ntable { border-collapse: collapse; width: 100%; }\nth, td { border: 1px solid black; padding: 8px; }\n</style>\n</head>\n<body>\n<table id=\"data-table\"><tr><th>Loading...</th></tr></table>\n<script>\nfetch('data.csv')\n    .then(response => response.text())\n    .then(data => {\n        const rows = data.split('\\n').map(row => row.split(','));\n        const table = document.getElementById('data-table');\n        table.innerHTML = '';\n        rows.forEach(row => {\n            const tr = document.createElement('tr');\n            row.forEach(cell => {\n                const td = document.createElement('td');\n                td.textContent = cell;\n                tr.appendChild(td);\n            });\n            table.appendChild(tr);\n        });\n    })\n    .catch(err => {\n        console.error(err);\n        const table = document.getElementById('data-table');\n        table.innerHTML = '<tr><td colspan=\"5\">Error: Unable to load data</td></tr>';\n    });\n</script>\n</body>\n</html>"
            )
        else:  # julia
            code_prompt = (
                "Write a Julia script using Genie.jl for a web API with a single /hello endpoint that returns 'Hello, World!' as JSON, "
                "and a /data endpoint that reads data.csv (an Iris dataset) using DataFrames.jl and CSV.jl and returns the first 5 rows as JSON. "
                "If data.csv is missing, return Dict('error' => 'Dataset not found'). "
                "Use the absolute path '/Users/craig/flowtest/data.csv' for reading the dataset. "
                "Set the port to 8000 explicitly using `Genie.config.server_port = 8000`. "
                "Start the server using `Genie.up()` (do not use `Genie.startup()`). "
                "Output only the Julia code, no markdown or code fences. "
                "Example:\nusing Genie, Genie.Renderer.Json, DataFrames, CSV, FilePaths\nGenie.config.server_port = 8000\nroute(\"/hello\") do\n    json(Dict(\"message\" => \"Hello, World!\"))\nend\nroute(\"/data\") do\n    if isfile(\"/Users/craig/flowtest/data.csv\")\n        df = CSV.read(\"/Users/craig/flowtest/data.csv\", DataFrame)\n        json(first(df, 5))\n    else\n        json(Dict(\"error\" => \"Dataset not found\"))\n    end\nend\nGenie.up()\n"
            )
        code, code_model = generate_code(code_prompt, args.api_base, args.workspace, api_key, args.mode, args.language, args.code_model, workspace_config)
        code_file = f"{REPO_PATH}/app.py" if args.language == "python" else f"{REPO_PATH}/index.html" if args.language == "html" else f"{REPO_PATH}/app.jl"
        with open(code_file, "w") as f:
            f.write(code)
        logger.info("Generated and saved %s using model: %s", code_file, code_model)

        # Generate tests
        if args.language == "python":
            test_prompt = (
                "Write pytest tests for a Flask API defined in app.py with /hello and /data endpoints. "
                "The /hello endpoint returns 'Hello, World!' as JSON. The /data endpoint returns the first 5 rows of data.csv as JSON if available, "
                "or {'error': 'Dataset not found'} if data.csv is missing. "
                "Use a pytest fixture to create a test client. Test both endpoints for status code 200 and correct JSON. "
                "Import Path from pathlib to check for data.csv existence. "
                "Ensure proper indentation for all code blocks with 4 spaces per level. "
                "Output only the Python code, no markdown, code fences, or explanatory text. "
                "Use relative import since app.py is in the parent directory. "
                "Example:\nfrom flask import Flask\nimport pytest\nfrom pathlib import Path\nfrom ..app import app\n\n@pytest.fixture\ndef client():\n    app.config['TESTING'] = True\n    with app.test_client() as client:\n        yield client\n\ndef test_hello_endpoint(client):\n    response = client.get('/hello')\n    assert response.status_code == 200\n    assert response.json == {'message': 'Hello, World!'}\n\ndef test_data_endpoint(client):\n    response = client.get('/data')\n    assert response.status_code == 200\n    if Path('data.csv').exists():\n        assert isinstance(response.json, dict)\n    else:\n        assert response.json == {'error': 'Dataset not found'}\n"
            )
        elif args.language == "html":
            test_prompt = (
                "Write Jest tests for a webpage that loads data.csv into a table using fetch. "
                "Test that the table loads the CSV data correctly. Use the jsdom environment for testing. "
                "Mock the fetch response to simulate loading CSV data. Do not use dynamic imports for HTML files. "
                "Directly include the JavaScript logic to manipulate the DOM in the test and verify the result. "
                "Output only the JavaScript code, no markdown or code fences. "
                "Example:\n/** @jest-environment jsdom */\ndescribe('Data Table', () => {\n    beforeEach(() => {\n        document.body.innerHTML = '<table id=\"data-table\"><tr><th>Loading...</th></tr></table>';\n        global.fetch = jest.fn(() =>\n            Promise.resolve({\n                text: () => Promise.resolve('1,2,3\\n4,5,6')\n            })\n        );\n    });\n    test('loads CSV into table', () => {\n        return fetch('data.csv')\n            .then(response => response.text())\n            .then(data => {\n                const rows = data.split('\\n').map(row => row.split(','));\n                const table = document.getElementById('data-table');\n                table.innerHTML = '';\n                rows.forEach(row => {\n                    const tr = document.createElement('tr');\n                    row.forEach(cell => {\n                        const td = document.createElement('td');\n                        td.textContent = cell;\n                        tr.appendChild(td);\n                    });\n                    table.appendChild(tr);\n                });\n                expect(table.querySelectorAll('tr').length).toBe(2);\n            });\n    });\n});"
            )
        else:  # julia
            test_prompt = (
                "Write a Julia test set for a Genie.jl API defined in app.jl with /hello and /data endpoints running on port 8000. "
                "The /hello endpoint returns 'Hello, World!' as JSON. The /data endpoint returns the first 5 rows of data.csv as JSON if available, "
                "or Dict('error' => 'Dataset not found') if data.csv is missing. "
                "Use Test.jl and HTTP.jl to test both endpoints for status code 200 and correct JSON. "
                "Include app.jl using the absolute path '/Users/craig/flowtest/app.jl' to ensure correct inclusion. "
                "Use the absolute path '/Users/craig/flowtest/data.csv' for checking the data file. "
                "When testing the /hello endpoint, convert the JSON response to a Dict and check the 'message' key. "
                "For the /data endpoint, if data.csv exists, check that the JSON response is a Dict with a 'columns' field containing arrays of data. "
                "Output only the Julia code, no markdown or code fences. "
                "Example:\nusing Test, HTTP, JSON3, FilePaths\ninclude(\"/Users/craig/flowtest/app.jl\")\n@testset \"Genie API\" begin\n    response = HTTP.get(\"http://localhost:8000/hello\")\n    @test response.status == 200\n    json_data = JSON3.read(response.body)\n    @test json_data.message == \"Hello, World!\"\n    response = HTTP.get(\"http://localhost:8000/data\")\n    @test response.status == 200\n    if isfile(\"/Users/craig/flowtest/data.csv\")\n        json_data = JSON3.read(response.body)\n        @test haskey(json_data, :columns)\n        @test length(json_data.columns) == 5\n    else\n        @test JSON3.read(response.body) == Dict(\"error\" => \"Dataset not found\")\n    end\nend\n"
            )
        tests, test_model = generate_code(test_prompt, args.api_base, args.workspace, api_key, args.mode, "javascript" if args.language == "html" else args.language, args.doc_model, workspace_config)
        os.makedirs(f"{REPO_PATH}/tests/{args.language}", exist_ok=True)
        if args.language != "html":
            with open(f"{REPO_PATH}/tests/{args.language}/__init__.py", "w") as f:
                f.write("")
        test_file = f"{REPO_PATH}/tests/{args.language}/test_app.py" if args.language == "python" else f"{REPO_PATH}/tests/{args.language}/test_index.test.js" if args.language == "html" else f"{REPO_PATH}/tests/{args.language}/test_app.jl"
        with open(test_file, "w") as f:
            f.write(tests)
        logger.info("Generated and saved %s using model: %s", test_file, test_model)

        # Run tests
        test_results = run_tests(args.language, args.http_port)
        print("Test Results:\n", test_results)

        # Generate documentation
        if args.language == "python":
            doc_prompt = (
                "Write a README.md file for a Flask API project with /hello and /data endpoints. "
                "The /hello endpoint returns 'Hello, World!' as JSON, and /data returns the first 5 rows of data.csv (an Iris dataset) as JSON if available, "
                "or an error message if missing. "
                "Include installation, running, and testing instructions. Output only the markdown content, no code fences around the entire markdown. "
                "Example:\n# Flask API\n\nA simple API with /hello and /data endpoints.\n\n## Installation\n\n1. Install Python 3.9+\n2. Install dependencies:\n```bash\npip install flask pandas\n```\n\n## Running\n\n1. Run the app:\n```bash\npython app.py\n```\n2. Access endpoints:\n```bash\ncurl http://localhost:5000/hello\ncurl http://localhost:5000/data\n```\n\n## Testing\n\nRun tests:\n```bash\npytest tests/python\n```"
            )
        elif args.language == "html":
            doc_prompt = (
                "Write a README.md file for a web app (index.html) that displays data.csv (Iris dataset) in a table using HTML5, CSS, and JavaScript. "
                "Include installation, running, and testing instructions. Output only the markdown content, no code fences around the entire markdown. "
                "Example:\n# Web App\n\nA simple web app displaying data.csv in a table.\n\n## Installation\n\n1. Install Node.js 16+\n2. Install dependencies:\n```bash\nnpm install\n```\n\n## Running\n\n1. Serve the app (e.g., using a local server):\n```bash\nnpx http-server -p 8081\n```\n2. Access the app:\n```bash\nopen http://localhost:8081\n```\n\n## Testing\n\nRun tests:\n```bash\nnpm test\n```"
            )
        else:  # julia
            doc_prompt = (
                "Write a README.md file for a Genie.jl API project with /hello and /data endpoints running on port 8000. "
                "The /hello endpoint returns 'Hello, World!' as JSON, and /data returns the first 5 rows of data.csv (an Iris dataset) as JSON if available, "
                "or an error message if missing. "
                "Include installation, running, and testing instructions. Output only the markdown content, no code fences around the entire markdown. "
                "Example:\n# Genie API\n\nA simple API with /hello and /data endpoints.\n\n## Installation\n\n1. Install Julia 1.11+\n2. Install dependencies:\n```bash\njulia -e \"using Pkg; Pkg.add([\\\"Genie\\\", \\\"DataFrames\\\", \\\"CSV\\\", \\\"Test\\\", \\\"HTTP\\\", \\\"JSON3\\\", \\\"FilePaths\\\"])\"\n```\n\n## Running\n\n1. Run the app:\n```bash\njulia --project=. app.jl\n```\n2. Access endpoints:\n```bash\ncurl http://localhost:8000/hello\ncurl http://localhost:8000/data\n```\n\n## Testing\n\nRun tests:\n```bash\njulia --project=. -e \"cd(\\\"tests/julia\\\"); include(\\\"test_app.jl\\\")\"\n```"
            )
        readme, doc_model = generate_code(doc_prompt, args.api_base, args.workspace, api_key, args.mode, args.language, args.doc_model, workspace_config)
        with open(f"{REPO_PATH}/README.md", "w") as f:
            f.write(readme)
        logger.info("Generated and saved README.md using model: %s", doc_model)

        # Generate requirements
        if args.language == "python":
            requirements = "flask\npandas\npytest\ngithub3.py\npsutil\n"
            with open(f"{REPO_PATH}/requirements.txt", "w") as f:
                f.write(requirements)
            repo.index.add(["requirements.txt"])
        elif args.language == "html":
            # Already handled package.json in run_tests
            pass
        else:  # julia
            pass  # Handled in run_tests

        # Generate GitHub Actions workflow
        generate_github_actions_workflow(repo, args.language)

        # Commit changes
        files_to_commit = ["app.py" if args.language == "python" else "index.html" if args.language == "html" else "app.jl", 
                           f"tests/{args.language}/__init__.py" if args.language != "html" else "package.json",
                           f"tests/{args.language}/test_app.py" if args.language == "python" else f"tests/{args.language}/test_index.test.js" if args.language == "html" else f"tests/{args.language}/test_app.jl", 
                           "README.md", 
                           "requirements.txt" if args.language == "python" else "Project.toml" if args.language == "julia" else "package.json"]
        if dataset_success and args.language in ["python", "html"]:
            files_to_commit.append("data.csv")
        repo.index.add(files_to_commit)
        repo.index.commit("Add API/WebApp, tests, docs, and dataset")
        logger.info("Changes committed to repository")
        print("Changes committed.")
    except Exception as e:
        logger.error("Workflow failed: %s", e)
        raise

if __name__ == "__main__":
    main()