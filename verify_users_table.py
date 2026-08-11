from sqlalchemy import inspect

from src.shared.database.session import get_engine


def main() -> None:
    print("=" * 60)
    print("VERIFYING USERS TABLE")
    print("=" * 60)

    engine = get_engine()
    inspector = inspect(engine)

    tables = inspector.get_table_names()

    print("\nTables in database:")

    for table in tables:
        print(f"  - {table}")

    if "users" not in tables:
        raise RuntimeError("users table was not found.")

    print("\nusers table exists.")

    print("\nColumns:")

    for column in inspector.get_columns("users"):
        print(
            f"  - {column['name']}: "
            f"{column['type']} "
            f"nullable={column['nullable']} "
            f"default={column['default']}"
        )

    print("\nIndexes:")

    for index in inspector.get_indexes("users"):
        print(
            f"  - {index['name']}: "
            f"columns={index['column_names']} "
            f"unique={index['unique']}"
        )

    print("\n" + "=" * 60)
    print("USERS TABLE VERIFICATION SUCCESSFUL")
    print("=" * 60)


if __name__ == "__main__":
    main()
