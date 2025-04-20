import subprocess
import os
import ast
import requests
import logging

logger = logging.getLogger(__name__)

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

def run_tests(repo_path, language, http_port=8081):
    """Run tests based on language."""
    try:
        test_dir = f"{repo_path}/tests/{language}"
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
            # Ensure PYTHONPATH includes the repo_path (/Users/craig/aix) to allow relative imports
            env["PYTHONPATH"] = f"{repo_path}:{env.get('PYTHONPATH', '')}"
            result = subprocess.run(
                ["pytest", f"tests/{language}", "--verbose"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                env=env
            )
        elif language == "html":
            package_json_path = os.path.join(repo_path, "package.json")
            if not os.path.exists(package_json_path):
                package_json_content = '''
                {
                  "name": "aix",
                  "version": "0.1.0",
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
            try:
                subprocess.run(["npm", "install", "jest@29.7.0", "jest-environment-jsdom@29.7.0"], cwd=repo_path, check=True)
            except subprocess.CalledProcessError as e:
                logger.warning("Initial npm install failed: %s", e)
                subprocess.run(["npm", "install"], cwd=repo_path, check=True)
            result = subprocess.run(["npm", "list", "jest", "jest-environment-jsdom"], cwd=repo_path, capture_output=True, text=True)
            logger.info("npm list jest jest-environment-jsdom:\n%s", result.stdout)
            if "jest@29.7.0" not in result.stdout or "jest-environment-jsdom@29.7.0" not in result.stdout:
                logger.error("Failed to install jest or jest-environment-jsdom. Please install manually with: npm install jest@29.7.0 jest-environment-jsdom@29.7.0")
                return "Jest dependencies not installed"
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
                cwd=repo_path,
                capture_output=True,
                text=True
            )
        else:  # julia
            subprocess.run(
                ["julia", "--project=.", "-e", 'using Pkg; Pkg.Registry.update(); Pkg.add(["Genie", "DataFrames", "CSV", "Test", "HTTP", "JSON3", "FilePaths"]); Pkg.instantiate()'],
                cwd=repo_path,
                check=True
            )
            result = subprocess.run(
                ["julia", "--project=.", "-e", f'cd("{test_dir}"); include("test_app.jl")'],
                cwd=repo_path,
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