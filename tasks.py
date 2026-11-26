"""Cross-platform task runner (replaces a Makefile; works on Windows).

Usage: uv run python tasks.py <task> [extra args]

Tasks:
  dev         run the API with auto-reload
  worker      run the scheduled-jobs worker
  test        run pytest (extra args are passed through)
  lint        ruff check + ruff format --check + mypy
  format      ruff format + ruff check --fix
  createdb    create the DATABASE_URL database if missing
  migrate     alembic upgrade head
  makemigration "message"   alembic revision --autogenerate
  seed-admin  create the first admin user (see --help)
"""

import subprocess
import sys

PY = sys.executable

TASKS: dict[str, list[list[str]]] = {
    "dev": [[PY, "-m", "uvicorn", "app.main:app", "--reload"]],
    "worker": [[PY, "-m", "app.worker"]],
    "test": [[PY, "-m", "pytest"]],
    "lint": [
        [PY, "-m", "ruff", "check", "."],
        [PY, "-m", "ruff", "format", "--check", "."],
        [PY, "-m", "mypy"],
    ],
    "format": [[PY, "-m", "ruff", "format", "."], [PY, "-m", "ruff", "check", "--fix", "."]],
    "createdb": [[PY, "-m", "app.core.createdb"]],
    "migrate": [[PY, "-m", "alembic", "upgrade", "head"]],
    "makemigration": [[PY, "-m", "alembic", "revision", "--autogenerate", "-m"]],
    "seed-admin": [[PY, "-m", "app.features.users.cli", "seed-admin"]],
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in TASKS:
        print(__doc__)
        return 1
    name, extra = sys.argv[1], sys.argv[2:]
    commands = TASKS[name]
    for i, cmd in enumerate(commands):
        # extra args go to the last command of the task
        full = cmd + extra if i == len(commands) - 1 else cmd
        code = subprocess.call(full)  # noqa: S603
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
