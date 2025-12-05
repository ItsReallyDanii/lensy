import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class GitInfo:
    branch: str
    latest_commit: str
    dirty: bool
    remote: Optional[str]


def run_git(args: List[str], cwd: Path) -> Optional[str]:
    """Run a git command and return stripped stdout when successful."""
    result = subprocess.run([
        "git",
        *args,
    ], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def collect_git_info(root: Path) -> Optional[GitInfo]:
    """Gather basic git metadata; return None when not a git repo."""
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    if branch is None:
        return None

    latest_commit = run_git(["log", "-1", "--pretty=format:%h %s"], root) or "n/a"
    status_output = run_git(["status", "--porcelain"], root) or ""
    dirty = bool(status_output.strip())
    remote = run_git(["remote", "get-url", "origin"], root)

    return GitInfo(
        branch=branch,
        latest_commit=latest_commit,
        dirty=dirty,
        remote=remote,
    )


def collect_file_overview(root: Path) -> List[str]:
    """Collect a simple listing of top-level files and directories with hints."""
    entries: List[str] = []
    for path in sorted(root.iterdir()):
        if path.name == ".git":
            continue
        if path.is_dir():
            entries.append(f"{path.name}/")
        else:
            size_kb = path.stat().st_size / 1024
            entries.append(f"{path.name} ({size_kb:.1f} KB)")
    return entries


def collect_stats(root: Path) -> Dict[str, int]:
    """Walk the directory to count files and folders (excluding .git)."""
    files = 0
    dirs = 0
    for current, dirnames, filenames in os.walk(root):
        # Skip .git entirely
        dirnames[:] = [d for d in dirnames if d != ".git"]
        dirs += len(dirnames)
        files += len(filenames)
    return {"files": files, "dirs": dirs}


def format_summary(root: Path) -> str:
    """Compose a human-readable summary for the given path."""
    git_info = collect_git_info(root)
    file_listing = collect_file_overview(root)
    stats = collect_stats(root)

    lines = [f"Path: {root}"]
    if git_info:
        lines.extend(
            [
                f"Branch: {git_info.branch}",
                f"Latest commit: {git_info.latest_commit}",
                f"Remote: {git_info.remote or 'n/a'}",
                f"Working tree: {'dirty' if git_info.dirty else 'clean'}",
            ]
        )
    else:
        lines.append("Git: n/a (not a repository)")

    lines.extend(
        [
            "",
            f"Contents: {stats['files']} files in {stats['dirs']} directories",
            *[f"  - {entry}" for entry in file_listing],
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize the contents and git details of a directory.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to inspect (default: current directory)",
    )
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        parser.error(f"Path does not exist: {root}")

    print(format_summary(root))


if __name__ == "__main__":
    main()