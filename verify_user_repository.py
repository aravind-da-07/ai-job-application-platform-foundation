"""
Integration test for the UserRepository.

This test performs a complete CRUD cycle against the Supabase
PostgreSQL users table and cleans up the test record afterward.
"""

from uuid import uuid4

from src.modules.users.domain.entities.user import User
from src.modules.users.domain.repositories.user_repository import UserRepository
from src.modules.users.infrastructure.repositories.user_repository_impl import (
    SQLAlchemyUserRepository,
)
from src.shared.database.session import session_scope


TEST_EMAIL = f"repository-test-{uuid4().hex[:12]}@example.com"


def main() -> None:
    print("=" * 70)
    print("USER REPOSITORY INTEGRATION TEST")
    print("=" * 70)

    test_user_id = None

    with session_scope() as session:
        repository: UserRepository = SQLAlchemyUserRepository(session)

        # --------------------------------------------------------------
        # 1. CREATE
        # --------------------------------------------------------------

        print("\n[1/6] Creating test user...")

        user = User(
            full_name="Repository Test User",
            email=TEST_EMAIL,
            phone="+919999999999",
        )

        created_user = repository.create(user)

        test_user_id = created_user.id

        print("      CREATE successful")
        print(f"      ID: {created_user.id}")
        print(f"      Email: {created_user.email}")

        # --------------------------------------------------------------
        # 2. READ BY ID
        # --------------------------------------------------------------

        print("\n[2/6] Reading user by ID...")

        fetched_by_id = repository.get_by_id(created_user.id)

        assert fetched_by_id is not None
        assert fetched_by_id.id == created_user.id
        assert fetched_by_id.email == TEST_EMAIL

        print("      READ by ID successful")

        # --------------------------------------------------------------
        # 3. READ BY EMAIL
        # --------------------------------------------------------------

        print("\n[3/6] Reading user by email...")

        fetched_by_email = repository.get_by_email(TEST_EMAIL)

        assert fetched_by_email is not None
        assert fetched_by_email.id == created_user.id
        assert fetched_by_email.email == TEST_EMAIL

        print("      READ by email successful")

        # --------------------------------------------------------------
        # 4. UPDATE
        # --------------------------------------------------------------

        print("\n[4/6] Updating user...")

        updated_user = User(
            id=created_user.id,
            full_name="Updated Repository Test User",
            email=TEST_EMAIL,
            phone="+918888888888",
            auth_provider=created_user.auth_provider,
            is_active=created_user.is_active,
            email_verified=True,
        )

        saved_user = repository.update(updated_user)

        assert saved_user.id == created_user.id
        assert saved_user.full_name == "Updated Repository Test User"
        assert saved_user.phone == "+918888888888"
        assert saved_user.email_verified is True

        print("      UPDATE successful")

        # --------------------------------------------------------------
        # 5. LIST
        # --------------------------------------------------------------

        print("\n[5/6] Listing users...")

        users = repository.list_users()

        matching_users = [
            existing_user
            for existing_user in users
            if existing_user.id == created_user.id
        ]

        assert len(matching_users) == 1

        print(f"      LIST successful")
        print(f"      Total users returned: {len(users)}")

        # --------------------------------------------------------------
        # 6. DELETE
        # --------------------------------------------------------------

        print("\n[6/6] Deleting test user...")

        repository.delete(created_user.id)

        deleted_user = repository.get_by_id(created_user.id)

        assert deleted_user is None

        print("      DELETE successful")

    print("\n" + "=" * 70)
    print("USER REPOSITORY INTEGRATION TEST SUCCESSFUL")
    print("=" * 70)
    print(f"Test email: {TEST_EMAIL}")
    print("Test record was removed from the database.")
    print("=" * 70)


if __name__ == "__main__":
    main()
