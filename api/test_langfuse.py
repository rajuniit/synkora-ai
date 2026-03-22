"""
Test script to verify Langfuse integration is working.
"""

import asyncio
import os

from src.services.observability.langfuse_service import langfuse_service


async def test_langfuse():
    """Test Langfuse connection and trace creation."""

    print("=" * 60)
    print("LANGFUSE INTEGRATION TEST")
    print("=" * 60)

    # Check if Langfuse is enabled
    print(f"\n1. Langfuse Enabled: {langfuse_service.is_enabled()}")
    print(f"   Host: {os.getenv('LANGFUSE_HOST', 'Not set')}")
    print(f"   Public Key: {os.getenv('LANGFUSE_PUBLIC_KEY', 'Not set')[:10]}...")
    print(f"   Secret Key: {'Set' if os.getenv('LANGFUSE_SECRET_KEY') else 'Not set'}")

    if not langfuse_service.is_enabled():
        print("\n❌ Langfuse is not enabled. Check your environment variables.")
        return

    # Test observability config
    test_config = {"langfuse_enabled": True, "sample_rate": 1.0, "trace_tools": True, "trace_rag": True}

    print(f"\n2. Should Trace (100% sample rate): {langfuse_service.should_trace(test_config)}")

    # Create a test trace
    print("\n3. Creating test trace...")
    try:
        trace_id = langfuse_service.create_trace(
            name="test_trace",
            user_id="test_user",
            session_id="test_session",
            metadata={"test": True, "purpose": "verification"},
        )
        print(f"   ✅ Trace created: {trace_id}")

        # Create a test generation
        print("\n4. Creating test generation...")
        generation_id = langfuse_service.create_generation(
            name="test_generation",
            model="test-model",
            input_data={"prompt": "Hello, this is a test"},
            trace_id=trace_id,
            metadata={"test": True},
        )
        print(f"   ✅ Generation created: {generation_id}")

        # Update the generation with output
        print("\n5. Updating generation with output...")
        langfuse_service.update_generation(
            generation_id=generation_id,
            output_data={"response": "Test response"},
            usage={"input": 10, "output": 5, "total": 15},
        )
        print("   ✅ Generation updated")

        # Create a test span
        print("\n6. Creating test span...")
        span_id = langfuse_service.create_span(
            name="test_span", input_data={"operation": "test"}, trace_id=trace_id, metadata={"test": True}
        )
        print(f"   ✅ Span created: {span_id}")

        # Flush to ensure data is sent
        print("\n7. Flushing data to Langfuse...")
        langfuse_service.flush()
        print("   ✅ Data flushed")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print(f"\nView your trace at: {os.getenv('LANGFUSE_HOST', 'http://localhost:3001')}")
        print("Look for trace with name 'test_trace' and user_id 'test_user'")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_langfuse())
