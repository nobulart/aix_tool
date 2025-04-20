import git
import os
import github3
import logging
import shutil

logger = logging.getLogger(__name__)

def init_repo(repo_path, github_token, fork_repo=None, remote_url=None):
    """Initialize a Git repository, optionally forking a GitHub repo and setting remote."""
    try:
        # If the directory exists but is not a valid Git repository, reinitialize it
        if os.path.exists(repo_path):
            try:
                repo = git.Repo(repo_path)
                logger.info("Existing Git repository found at %s", repo_path)
            except git.exc.InvalidGitRepositoryError:
                logger.warning("Directory %s exists but is not a valid Git repository. Reinitializing...", repo_path)
                # Remove the directory and its contents
                shutil.rmtree(repo_path)
                # Create a new directory and initialize the Git repository
                os.makedirs(repo_path)
                repo = git.Repo.init(repo_path)
                with open(f"{repo_path}/README.md", "w") as f:
                    f.write("# Project\n")
                repo.index.add(["README.md"])
                repo.index.commit("Initial commit")
                logger.info("Initialized new Git repository at %s", repo_path)
        else:
            # Directory doesn't exist, create and initialize it
            os.makedirs(repo_path)
            repo = git.Repo.init(repo_path)
            with open(f"{repo_path}/README.md", "w") as f:
                f.write("# Project\n")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")
            logger.info("Initialized Git repository at %s", repo_path)

        # Ensure the branch is 'main'
        if repo.active_branch.name == "master":
            repo.git.checkout("-b", "main")
            logger.info("Renamed branch from 'master' to 'main'")
        elif repo.active_branch.name != "main":
            repo.git.checkout("main")

        # Create __init__.py for Python package structure
        init_file = os.path.join(repo_path, "__init__.py")
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
            clone_path = os.path.join(repo_path, repo_name)
            if os.path.exists(clone_path):
                logger.warning("Directory %s already exists. Skipping clone.", clone_path)
            else:
                git.Repo.clone_from(forked_repo.clone_url, clone_path)
                logger.info("Cloned forked repository to %s", clone_path)

        return repo
    except Exception as e:
        logger.error("Failed to initialize repository: %s", e)
        raise