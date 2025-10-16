"""File name validation script for GitHub Actions.

This script ensures all Python files follow naming conventions
(alphanumeric, underscores, and hyphens only).
"""

import os
import sys
import re

# Regular expression for valid file names (alphanumeric, underscores, and hyphens only)
VALID_FILENAME_REGEX = r'^[a-zA-Z0-9_\-]+\.py$'


def check_file_names():
    """Check all Python files for valid naming conventions."""
    invalid_files = []
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and not re.match(VALID_FILENAME_REGEX, file):
                invalid_files.append(os.path.join(root, file))

    if invalid_files:
        print("The following files have invalid names:")
        for file in invalid_files:
            print(f"- {file}")
        sys.exit(1)  # Exit with error


if __name__ == "__main__":
    check_file_names()
