"""Test Langfuse connection and configuration."""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.settings import settings

print("=" * 60)
print("Langfuse Configuration Test")
print("=" * 60)

print(f"\nLangfuse Enabled: {settings.langfuse_enabled}")
print(f"Langfuse Host: {settings.langfuse_host}")
print(f"Langfuse Public Key: {settings.langfuse_public_key[:10] if settings.langfuse_public_key else 'Not set'}...")
print(f"Langfuse Secret Key: {settings.langfuse_secret_key[:10] if settings.langfuse_secret_key else 'Not set'}...")
print(f"Langfuse Sample Rate: {settings.langfuse_sample_rate}")
print(f"Is Configured: {settings.is_configured}")

if settings.is_configured:
    print("\n✅ Langfuse is properly configured!")

    # Try to initialize the client
    try:
        from langfuse import Langfuse

        print("\nAttempting to connect to Langfuse...")
        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )

        # Try to create a test trace
        trace = client.trace(name="test_connection")
        print(f"✅ Successfully connected! Test trace ID: {trace.id}")
        print(f"View trace at: {settings.langfuse_host}/trace/{trace.id}")

        # Flush to ensure it's sent
        client.flush()
        print("✅ Trace flushed successfully!")

    except Exception as e:
        print(f"❌ Failed to connect to Langfuse: {e}")
        import traceback

        traceback.print_exc()
else:
    print("\n❌ Langfuse is not properly configured!")
    print("\nPlease ensure the following environment variables are set:")
    print("  - LANGFUSE_ENABLED=true")
    print("  - LANGFUSE_PUBLIC_KEY=<your-public-key>")
    print("  - LANGFUSE_SECRET_KEY=<your-secret-key>")
    print("  - LANGFUSE_HOST=http://langfuse-web:3000 (for Docker)")

print("\n" + "=" * 60)
