"""site2skill - Turn any documentation website into a Claude Agent Skill."""

import os
import stat
import subprocess
import sys
from pathlib import Path


def get_binary_path() -> Path:
    """Return the path to the bundled binary."""
    package_dir = Path(__file__).parent
    binary = package_dir / "bin" / "site2skill"

    # Ensure binary is executable on Unix
    if sys.platform != "win32":
        if binary.exists():
            current_mode = os.stat(binary).st_mode
            if not (current_mode & stat.S_IXUSR):
                os.chmod(
                    binary, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                )

    return binary


def main():
    """Execute the bundled binary."""
    binary = get_binary_path()

    if not binary.exists():
        print(f"Error: Binary not found at {binary}", file=sys.stderr)
        sys.exit(1)

    if sys.platform == "win32":
        # On Windows, use subprocess to properly handle signals
        result = subprocess.run([str(binary)] + sys.argv[1:])
        sys.exit(result.returncode)
    else:
        # On Unix, exec replaces the process
        os.execvp(str(binary), [str(binary)] + sys.argv[1:])


if __name__ == "__main__":
    main()
