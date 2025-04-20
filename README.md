# AIX Toolset

The AIX Toolset is a modular, model-agnostic Python-based automation framework designed to streamline code generation, testing, documentation, and version control for projects in HTML/JavaScript, Python, and Julia. It leverages the AnythingLLM API to generate code, integrates datasets, runs tests, generates documentation, sets up CI workflows, and manages Git operations. This toolset is ideal for tasks such as adding GPU support to existing Julia libraries, forking repositories, and automating development workflows.

## Overview

The AIX Toolset automates the development lifecycle by providing a unified workflow for:

- **Forking and Cloning Repositories**: Fork GitHub repositories to your account and clone them locally.
- **Code Generation**: Generate code in HTML/JavaScript, Python (Flask), or Julia (Genie.jl) using the AnythingLLM API.
- **Dataset Integration**: Download and integrate datasets (e.g., Iris dataset) for use in generated applications.
- **Testing**: Run Jest tests for HTML, pytest for Python, and Julia tests for Genie.jl applications.
- **Documentation**: Generate a `README.md` with setup, running, and testing instructions.
- **CI Setup**: Create GitHub Actions workflows for continuous integration.
- **Version Control**: Initialize a Git repository, commit changes, and push to a remote repository.

The toolset is model-agnostic, allowing you to specify any chat or agent model supported by AnythingLLM for code and documentation generation.

## Components

The AIX Toolset consists of the following components, located in the `aix/` directory:

- **`main.py`**: The entry point of the toolset. It orchestrates the workflow, including forking, cloning, code generation, testing, documentation, and Git operations.
- **`api.py`**: Handles interactions with the AnythingLLM API for code and documentation generation.
- **`codegen.py`**: Processes and formats generated code, ensuring proper syntax and style (e.g., using `autopep8` for Python).
- **`dataset.py`**: Downloads datasets (e.g., Iris dataset) for use in generated applications.
- **`git_utils.py`**: Manages Git operations, including forking, cloning, initializing repositories, committing, and pushing changes.
- **`test_runner.py`**: Executes tests for generated code (Jest for HTML, pytest for Python, Julia tests for Genie.jl).
- **`ci.py`**: Generates GitHub Actions workflows for continuous integration.
- **`utils.py`**: Provides utility functions, such as RAM usage checks and user prompts for model management.
- **Scripts**:
  - `run_workflow.sh`: Runs the toolset for a single language.
  - `run_tests.sh`: Executes the full workflow and tests for all supported languages (HTML, Python, Julia).
  - `setup_env.sh`: Sets up the Python virtual environment and installs dependencies.

## Prerequisites

- **Python 3.9+**: Required to run the toolset.
- **Node.js 16+**: Required for HTML/JavaScript testing with Jest.
- **Julia 1.11+**: Required for Julia/Genie.jl applications.
- **AnythingLLM API**: Requires an API key set as the `ANYTHINGLLM_API_KEY` environment variable.
- **GitHub Token**: Requires a token set as the `GITHUB_TOKEN` environment variable with `repo` scope for Git operations (forking, cloning, pushing).
- **LM Studio**: Used for model inference; ensure your desired models are loaded and compatible with AnythingLLM.

## Installation

1. Clone the AIX Toolset repository to your local machine:

   ```bash
   git clone https://github.com/nobulart/aix_tool.git
   cd aix_tool
   ```

2. Set up the Python virtual environment:

   ```bash
   bash scripts/setup_env.sh
   ```

3. Activate the virtual environment:

   ```bash
   source ~/aix_env/bin/activate
   ```

4. Set environment variables for AnythingLLM and GitHub:

   ```bash
   export ANYTHINGLLM_API_KEY="your-anythingllm-api-key"
   export GITHUB_TOKEN="your-github-token"
   ```

## Usage

The toolset is executed via `main.py`, with options specified through command-line arguments. Convenience scripts are provided for common workflows:

- `run_workflow.sh`: Runs the workflow for a specific language.
- `run_tests.sh`: Executes the workflow and tests for all languages sequentially.

### Command-Line Options

| Option            | Description                                      | Default Value                       | Choices/Examples                     |
|-------------------|--------------------------------------------------|-------------------------------------|--------------------------------------|
| `--code-model`    | Model for code generation (overrides workspace default) | None                                | `my-code-model`                     |
| `--doc-model`     | Model for documentation generation (overrides workspace default) | None                                | `my-doc-model`                      |
| `--chat-model`    | Override the default chat model used by AnythingLLM | None                                | `codellama-13b`                     |
| `--agent-model`   | Override the default agent model used by AnythingLLM | None                                | `llama-3-groq-8b-tool-use`          |
| `--api-base`      | AnythingLLM API base URL                      | `http://localhost:3001`             | `http://localhost:3001`             |
| `--workspace`     | Workspace slug for API requests               | `development`                       | `development`                       |
| `--mode`          | Chat mode for API requests                    | `chat`                              | `chat`, `agent`                     |
| `--language`      | Programming language to generate code for     | `python`                            | `python`, `julia`, `html`           |
| `--fork-repo`     | GitHub repository to fork (e.g., `user/repo`) | None                                | `CliMA/Oceananigans.jl`             |
| `--remote-url`    | Git remote URL for pushing changes            | `https://github.com/nobulart/aix.git` | `https://github.com/nobulart/Oceananigans.jl` |
| `--http-port`     | Port for the HTTP server (HTML apps)          | `8081`                              | `8081`                              |

### Workflow Breakdown

The AIX Toolset follows this workflow when executed:

1. **Fork and Clone**:
   - If `--fork-repo` is specified, forks the repository to your GitHub account using `GITHUB_TOKEN`.
   - Initializes a Git repository at `/Users/craig/aix` (or the specified directory) and clones the forked repository.
   - Sets the remote URL for pushing changes using `--remote-url`.

2. **Code Generation**:
   - Uses the AnythingLLM API to generate code based on a prompt tailored to the specified `--language`.
   - For Julia, generates code compatible with Genie.jl or other frameworks as specified in the prompt.
   - Saves the generated code to a file (e.g., `app.jl` for Julia).

3. **Dataset Integration**:
   - Downloads datasets (e.g., Iris dataset) if required by the prompt (optional for Julia projects).

4. **Testing**:
   - Generates tests based on a prompt and saves them to `/Users/craig/aix/tests/<language>/`.
   - Executes tests using Jest (HTML), pytest (Python), or Julia’s `Test.jl` (Julia).

5. **Documentation**:
   - Generates a `README.md` with setup, running, and testing instructions, saved to `/Users/craig/aix/README.md`.

6. **Git Operations**:
   - Commits generated files (code, tests, documentation) to the local repository.
   - Pushes changes to the specified `--remote-url` on the `main` branch.

### Example: Adding Metal Support to a Julia Library

Here’s an example of using the AIX Toolset to add Metal (Apple Silicon) support to a Julia library like Oceananigans.jl:

1. **Fork the Repository**:
   Fork the Oceananigans.jl repository to your GitHub account:

   ```bash
   cd /Users/craig/aix_tool
   bash scripts/run_workflow.sh --language julia --fork-repo CliMA/Oceananigans.jl --remote-url https://github.com/nobulart/Oceananigans.jl --chat-model codellama-13b --agent-model llama-3-groq-8b-tool-use
   ```

   This command forks `CliMA/Oceananigans.jl` to `nobulart/Oceananigans.jl`, clones it to `/Users/craig/aix`, and sets up the remote URL for pushing changes.

2. **Set Up Julia Dependencies**:
   Activate the Julia project environment and install dependencies:

   ```bash
   cd /Users/craig/aix
   julia --project="."
   julia> using Pkg
   julia> Pkg.add("Oceananigans")
   julia> Pkg.add("Metal")
   julia> Pkg.instantiate()
   ```

3. **Generate Code for Metal Support**:
   Modify the `main.py` prompt to generate code for Metal support, or run a custom workflow to generate the code directly. For example, edit `main.py` to include a prompt for generating Metal.jl code, then run:

   ```bash
   bash scripts/run_workflow.sh --language julia --remote-url https://github.com/nobulart/Oceananigans.jl --chat-model codellama-13b --agent-model llama-3-groq-8b-tool-use
   ```

   This generates a file (e.g., `metal_support.jl`) with Metal.jl integration for Oceananigans.jl.

4. **Generate Tests**:
   Tests are automatically generated as part of the workflow and saved to `/Users/craig/aix/tests/julia/`. The workflow executes these tests using Julia’s `Test.jl`.

5. **Generate Documentation**:
   A `README.md` is generated with instructions for setting up and running the Metal-supported code, saved to `/Users/craig/aix/README.md`.

6. **Commit and Push**:
   The workflow commits all changes and pushes them to `https://github.com/nobulart/Oceananigans.jl` on the `main` branch.

### Troubleshooting

- **Julia Server Timing Issues**:
  - If `curl` commands to the Julia app fail with `Couldn't connect to server`, the server may not have started in time. The `run_tests.sh` script includes a retry loop with a 15-second initial sleep:
    ```bash
    sleep 15
    for i in {1..3}; do curl http://localhost:8000/hello && break || sleep 5; done
    ```
  - If the issue persists, increase the sleep time or investigate Julia server startup delays (e.g., precompile dependencies with `Pkg.precompile()`).

- **Dependency Installation**:
  - Ensure Julia dependencies are installed correctly:
    ```bash
    julia --project="."
    julia> using Pkg
    julia> Pkg.add(["Oceananigans", "Metal", "Test"])
    ```
  - If Metal.jl fails to install, verify Julia version (v1.6+ required for Apple Silicon) and check for Metal.jl updates on GitHub.

- **Git Push Failures**:
  - If pushing to the remote repository fails, verify the `GITHUB_TOKEN` has `repo` scope:
    ```bash
    curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
    ```
  - Use SSH if HTTPS fails:
    ```bash
    git remote remove origin
    git remote add origin git@github.com:nobulart/Oceananigans.jl.git
    git push -u origin main
    ```

## Contributing

Contributions are welcome! Please fork the repository, make your changes, and submit a pull request to `https://github.com/nobulart/aix_tool`.

## License

This project is licensed under the MIT License.