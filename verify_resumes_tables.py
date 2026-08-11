"""
Verify the resumes and resume_versions database schema.

This script checks the actual PostgreSQL database rather than only
checking SQLAlchemy metadata.
"""

from sqlalchemy import inspect

from src.shared.database.session import get_engine


def main() -> None:
    print("=" * 60)
    print("VERIFYING RESUME DATABASE TABLES")
    print("=" * 60)

    engine = get_engine()
    inspector = inspect(engine)

    tables = inspector.get_table_names()

    print("\nTables in database:")
    for table in tables:
        print(f"- {table}")

    required_tables = {
        "users",
        "resumes",
        "resume_versions",
    }

    missing_tables = required_tables - set(tables)

    if missing_tables:
        raise RuntimeError(
            f"Missing required tables: {sorted(missing_tables)}"
        )

    print("\nRequired tables exist.")

    for table_name in ("resumes", "resume_versions"):
        print(f"\n{'-' * 60}")
        print(f"TABLE: {table_name}")
        print(f"{'-' * 60}")

        columns = inspector.get_columns(table_name)

        print("\nColumns:")

        for column in columns:
            print(
                f"- {column['name']}: "
                f"{column['type']} "
                f"nullable={column['nullable']} "
                f"default={column['default']}"
            )

        indexes = inspector.get_indexes(table_name)

        print("\nIndexes:")

        if not indexes:
            print("- None")
        else:
            for index in indexes:
                print(
                    f"- {index['name']}: "
                    f"columns={index['column_names']} "
                    f"unique={index['unique']}"
                )

        foreign_keys = inspector.get_foreign_keys(table_name)

        print("\nForeign keys:")

        if not foreign_keys:
            print("- None")
        else:
            for foreign_key in foreign_keys:
                print(
                    f"- {foreign_key['name']}: "
                    f"{foreign_key['constrained_columns']} "
                    f"-> "
                    f"{foreign_key['referred_table']}."
                    f"{foreign_key['referred_columns']}"
                )

    print("\n" + "=" * 60)
    print("✅ RESUME DATABASE SCHEMA VERIFIED")
    print("=" * 60)


if __name__ == "__main__":
    main()