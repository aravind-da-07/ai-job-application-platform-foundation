from src.modules.users.domain.entities.user import AuthProvider, User


user = User(
    full_name="Aravind Reddy",
    email="aravind@example.com",
    phone="+91XXXXXXXXXX",
    auth_provider=AuthProvider.LOCAL,
)

print("=" * 60)
print("USER DOMAIN ENTITY")
print("=" * 60)

print(user)

print()
print("ID:", user.id)
print("Name:", user.full_name)
print("Email:", user.email)
print("Provider:", user.auth_provider.value)
print("Active:", user.is_active)
print("Email verified:", user.email_verified)