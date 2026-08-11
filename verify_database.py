"""
Temporary verification script for checking the SQLAlchemy connection
to the Supabase PostgreSQL database.
"""

from src.shared.database.session import check_database_health

print("=" * 60)
print("Checking connection to Supabase PostgreSQL...")
print("=" * 60)

try:
    if check_database_health():
        print("✅ SUCCESS!")
        print("Database connection established successfully.")
except Exception as exc:
    print("❌ FAILED!")
    print(exc)