import os
import sys
import argparse
from pathlib import Path
from aix.api import check_api_availability
from aix.codegen import generate_code
from aix.dataset import download_dataset
from aix.git_utils import init_repo
from aix.test_runner import run_tests
from aix.ci import generate_github_actions_workflow
from aix.utils import initial_model_check, logger

REPO_PATH = os.path.expanduser("~/aix")
LM_STUDIO_API = "http://localhost:1234"

def main():
    parser = argparse.ArgumentParser(description="Agentic workflow for code generation, testing, and dataset integration")
    parser.add_argument("--code-model", help="Model for code generation (overrides workspace default)")
    parser.add_argument("--doc-model", help="Model for documentation generation (overrides workspace default)")
    parser.add_argument("--chat-model", help="Override the default chat model used by AnythingLLM")
    parser.add_argument("--agent-model", help="Override the default agent model used by AnythingLLM")
    parser.add_argument("--api-base", default="http://localhost:3001", help="AnythingLLM API base URL")
    parser.add_argument("--workspace", default="development", help="Workspace slug for API requests")
    parser.add_argument("--mode", default="chat", choices=["chat", "agent"], help="Chat mode (chat or agent)")
    parser.add_argument("--language", default="python", choices=["python", "julia", "html"], help="Programming language (python, julia, or html)")
    parser.add_argument("--fork-repo", help="GitHub repository to fork (e.g., user/repo)")
    parser.add_argument("--remote-url", default="https://github.com/nobulart/aix.git", help="Git remote URL for pushing changes")
    parser.add_argument("--http-port", default="8081", type=int, help="Port for the HTTP server (default: 8081)")
    args = parser.parse_args()

    os.chdir(REPO_PATH)

    api_key = os.getenv("ANYTHINGLLM_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    if not api_key:
        logger.error("ANYTHINGLLM_API_KEY environment variable not set")
        sys.exit(1)

    is_available, workspace_config = check_api_availability(args.api_base, args.workspace, api_key)
    if not is_available:
        logger.error("Aborting due to inaccessible API or invalid workspace")
        sys.exit(1)

    if args.mode == "agent" and (not workspace_config or not workspace_config.get("agent_provider")):
        logger.warning("Agent mode selected but no agent provider configured. Falling back to chat mode.")
        args.mode = "chat"

    try:
        initial_model_check()
        repo = init_repo(REPO_PATH, github_token, args.fork_repo, args.remote_url)

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
            dataset_success = True

        if args.language == "python":
            code_prompt = (
                "Write a Python script for a Flask REST API with a single /hello endpoint that returns 'Hello, World!' as JSON, "
                "and a /data endpoint that reads data.csv (an Iris dataset) using pandas and returns the first 5 rows as JSON. "
                "If data.csv is missing, return {'error': 'Dataset not found'}. "
                "Use Flask's jsonify and ensure the app can be run with `app.run(port=int(os.getenv('FLASK_PORT', 5000)))`. "
                "Ensure proper indentation for all code blocks with 4 spaces per level. "
                "Output only the Python code, no markdown, code fences, or explanatory text. "
                "Example:\nfrom flask import Flask, jsonify\nimport pandas as pd\nimport os\nfrom pathlib import Path\napp = Flask(__name__)\n@app.route('/hello')\ndef hello():\n    return jsonify({'message': 'Hello, World!'})\n@app.route('/data')\ndef data():\n    if Path('data.csv').exists():\n        df = pd.read_csv('data.csv')\n        return jsonify(df.head().to_dict())\n    return jsonify({'error': 'Dataset not found'})\nif __name__ == '__main__':\n    app.run(port=int(os.getenv('FLASK_PORT', 5000)))"
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
                "Use the absolute path '/Users/craig/aix/data.csv' for reading the dataset. "
                "Set the port to 8000 explicitly using `Genie.config.server_port = 8000`. "
                "Start the server using `Genie.up()` (do not use `Genie.startup()`). "
                "Output only the Julia code, no markdown or code fences. "
                "Example:\nusing Genie, Genie.Renderer.Json, DataFrames, CSV, FilePaths\nGenie.config.server_port = 8000\nroute(\"/hello\") do\n    json(Dict(\"message\" => \"Hello, World!\"))\nend\nroute(\"/data\") do\n    if isfile(\"/Users/craig/aix/data.csv\")\n        df = CSV.read(\"/Users/craig/aix/data.csv\", DataFrame)\n        json(first(df, 5))\n    else\n        json(Dict(\"error\" => \"Dataset not found\"))\n    end\nend\nGenie.up()\n"
            )
        code, code_model = generate_code(code_prompt, args.api_base, args.workspace, api_key, args.mode, args.language, args.code_model, workspace_config)
        code_file = f"{REPO_PATH}/app.py" if args.language == "python" else f"{REPO_PATH}/index.html" if args.language == "html" else f"{REPO_PATH}/app.jl"
        with open(code_file, "w") as f:
            f.write(code)
        logger.info("Generated and saved %s", code_file)

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
                "Include app.jl using the absolute path '/Users/craig/aix/app.jl' to ensure correct inclusion. "
                "Use the absolute path '/Users/craig/aix/data.csv' for checking the data file. "
                "When testing the /hello endpoint, convert the JSON response to a Dict and check the 'message' key. "
                "For the /data endpoint, if data.csv exists, check that the JSON response is a Dict with a 'columns' field containing arrays of data. "
                "Output only the Julia code, no markdown or code fences. "
                "Example:\nusing Test, HTTP, JSON3, FilePaths\ninclude(\"/Users/craig/aix/app.jl\")\n@testset \"Genie API\" begin\n    response = HTTP.get(\"http://localhost:8000/hello\")\n    @test response.status == 200\n    json_data = JSON3.read(response.body)\n    @test json_data.message == \"Hello, World!\"\n    response = HTTP.get(\"http://localhost:8000/data\")\n    @test response.status == 200\n    if isfile(\"/Users/craig/aix/data.csv\")\n        json_data = JSON3.read(response.body)\n        @test haskey(json_data, :columns)\n        @test length(json_data.columns) == 5\n    else\n        @test JSON3.read(response.body) == Dict(\"error\" => \"Dataset not found\")\n    end\nend\n"
            )
        tests, test_model = generate_code(test_prompt, args.api_base, args.workspace, api_key, args.mode, "javascript" if args.language == "html" else args.language, args.doc_model, workspace_config)
        os.makedirs(f"{REPO_PATH}/tests/{args.language}", exist_ok=True)
        if args.language != "html":
            with open(f"{REPO_PATH}/tests/{args.language}/__init__.py", "w") as f:
                f.write("")
        test_file = f"{REPO_PATH}/tests/{args.language}/test_app.py" if args.language == "python" else f"{REPO_PATH}/tests/{args.language}/test_index.test.js" if args.language == "html" else f"{REPO_PATH}/tests/{args.language}/test_app.jl"
        with open(test_file, "w") as f:
            f.write(tests)
        logger.info("Generated and saved %s", test_file)

        # Run tests
        test_results = run_tests(REPO_PATH, args.language, args.http_port)
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
        logger.info("Generated and saved README.md")

        # Generate requirements
        if args.language == "python":
            requirements = "flask\npandas\npytest\ngithub3.py\npsutil\n"
            with open(f"{REPO_PATH}/requirements.txt", "w") as f:
                f.write(requirements)
            repo.index.add(["requirements.txt"])
        elif args.language == "html":
            pass  # Already handled package.json in run_tests
        else:  # julia
            pass  # Handled in run_tests

        # Generate GitHub Actions workflow
        generate_github_actions_workflow(repo, args.language, REPO_PATH)

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