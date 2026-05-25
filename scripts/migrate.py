import os
import subprocess
import sys

def main():
    print("Running Alembic migrations (migrate)...")
    os.environ["PYTHONPATH"] = "."
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=".")
    if result.returncode != 0:
        print("Migration failed.")
        sys.exit(1)
    print("Migration successful.")

if __name__ == "__main__":
    main()