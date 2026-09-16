import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "job_bot"))

from db import ensure_database


if __name__ == "__main__":
    ensure_database()
    print("Migration check completed.")
