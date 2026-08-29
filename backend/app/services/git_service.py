"""Git repository management: every project can own a server-side bare repo."""
import logging
import os
import subprocess
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class GitServiceError(Exception):
    pass


def _run_git(args: "list[str]", cwd: Optional[str] = None) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise GitServiceError("git 命令不可用, 请安装 git") from exc
    if proc.returncode != 0:
        raise GitServiceError(f"git {' '.join(args)} 失败: {proc.stderr.strip()}")
    return proc.stdout.strip()


def repo_dir(project_key: str) -> str:
    base = os.path.abspath(settings.REPOS_DIR)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{project_key}.git")


def init_repo(project_key: str) -> str:
    """Create a bare repo with the configured initial branch. Idempotent."""
    path = repo_dir(project_key)
    if os.path.exists(os.path.join(path, "HEAD")):
        return path
    args = ["init", "--bare", "-b", settings.GIT_INITIAL_BRANCH, path]
    _run_git(args)
    with open(os.path.join(path, "description"), "w", encoding="utf-8") as f:
        f.write(f"PrjHub project {project_key}\n")
    logger.info("initialized bare git repo for %s at %s", project_key, path)
    return path


def delete_repo(project_key: str) -> bool:
    import shutil

    path = repo_dir(project_key)
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        return True
    return False


def repo_info(project_key: str) -> Optional[dict]:
    path = repo_dir(project_key)
    if not os.path.exists(os.path.join(path, "HEAD")):
        return None
    branch = settings.GIT_INITIAL_BRANCH
    try:
        head = open(os.path.join(path, "HEAD"), encoding="utf-8").read().strip()
        if head.startswith("ref: refs/heads/"):
            branch = head.split("/")[-1]
    except OSError:
        pass
    try:
        size_kb = sum(
            os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(path) for f in files
        ) // 1024
    except OSError:
        size_kb = 0
    return {"path": path, "branch": branch, "size_kb": size_kb}
