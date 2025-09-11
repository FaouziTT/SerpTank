#!/usr/bin/env python3
"""
Run database migrations to create missing tables.
"""
import subprocess
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def run_migrations():
    """Run alembic migrations."""
    print("Running database migrations...")
    
    try:
        # Run alembic upgrade to latest
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print("✅ Migrations completed successfully!")
            print(result.stdout)
        else:
            print("❌ Migration failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
        # Check current migration status
        print("\nChecking migration status...")
        status_result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        print("Current migration status:")
        print(status_result.stdout)
        
        return True
        
    except Exception as e:
        print(f"Error running migrations: {e}")
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)