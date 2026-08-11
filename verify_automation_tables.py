"""
Verify automation tables in the real PostgreSQL/Supabase database.
"""

from sqlalchemy import inspect

from src.shared.database.session import session_scope


def main() -> None:
    print("=" * 70)
    print("VERIFYING AUTOMATION DATABASE TABLES")
    print("=" * 70)

    with session_scope() as session:
        inspector = inspect(session.bind)

        tables = inspector.get_table_names()

        print("\nTables in database:")

        for table in tables:
            print(f"- {table}")

        required_tables = {
            "automation_runs",
            "automation_logs",
        }

        missing_tables = required_tables - set(tables)

        if missing_tables:
            raise RuntimeError(
                f"Missing automation tables: {sorted(missing_tables)}"
            )

        print("\nRequired automation tables exist.")

        for table_name in (
            "automation_runs",
            "automation_logs",
        ):
            print("\n" + "-" * 70)
            print(f"TABLE: {table_name}")
            print("-" * 70)

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

            for index in indexes:
                print(
                    f"- {index['name']}: "
                    f"columns={index['column_names']} "
                    f"unique={index['unique']}"
                )

            foreign_keys = inspector.get_foreign_keys(table_name)

            print("\nForeign keys:")

            for foreign_key in foreign_keys:
                print(
                    f"- {foreign_key['name']}: "
                    f"{foreign_key['constrained_columns']} "
                    f"-> "
                    f"{foreign_key['referred_table']}."
                    f"{foreign_key['referred_columns']} "
                    f"ondelete={foreign_key.get('options', {}).get('ondelete')}"
                )

    print("\n" + "=" * 70)
    print("AUTOMATION DATABASE VERIFICATION PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()