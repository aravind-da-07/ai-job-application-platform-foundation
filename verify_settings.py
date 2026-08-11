from src.shared.config.settings import get_settings

settings = get_settings()

print("=" * 50)
print("APP NAME:", settings.app_name)
print("ENVIRONMENT:", settings.environment)
print("DATABASE URL EXISTS:", bool(settings.database_url))
print("SUPABASE URL:", settings.supabase_url)
print("SUPABASE ANON EXISTS:", bool(settings.supabase_anon_key))
print("SERVICE ROLE EXISTS:", bool(settings.supabase_service_role_key))
print("=" * 50)