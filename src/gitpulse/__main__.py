"""Allow running the CLI with ``python -m gitpulse``."""

from gitpulse.cli import app

if __name__ == "__main__":
    app(prog_name="gitpulse")
