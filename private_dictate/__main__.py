"""Allow `python -m private_dictate` as a daemon alias."""
from private_dictate.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
