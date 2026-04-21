"""Allow `python -m dictate` as a daemon alias."""
from dictate.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
