import os
import logging

logger = logging.getLogger(__name__)

def generate_github_actions_workflow(repo, language, repo_path):
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
    workflow_path = os.path.join(repo_path, ".github/workflows/ci.yml")
    os.makedirs(os.path.dirname(workflow_path), exist_ok=True)
    with open(workflow_path, "w") as f:
        f.write(workflow_content.strip())
    repo.index.add([".github/workflows/ci.yml"])
    repo.index.commit("Add GitHub Actions CI workflow")
    logger.info("Generated GitHub Actions workflow at %s", workflow_path)