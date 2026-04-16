"""Tests for FunctionCallingErrorTracker."""


from src.services.agents.error_tracker import FunctionCallingErrorTracker


class TestFunctionCallingErrorTracker:
    """Tests for FunctionCallingErrorTracker class."""

    def test_initialization_default(self):
        """Test default initialization."""
        tracker = FunctionCallingErrorTracker()
        assert tracker.max_repeated_errors == 3
        assert tracker.error_counts == {}

    def test_initialization_custom_max_errors(self):
        """Test initialization with custom max_repeated_errors."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=5)
        assert tracker.max_repeated_errors == 5
        assert tracker.error_counts == {}

    def test_track_error_non_parameter_error(self):
        """Test tracking a non-parameter error — stored under tool:message key."""
        tracker = FunctionCallingErrorTracker()

        result = tracker.track_error("test_tool", "Some other error")

        assert result is False
        assert len(tracker.error_counts) == 1
        assert tracker.error_counts["test_tool:Some other error"] == 1

    def test_track_error_parameter_validation_single(self):
        """Test tracking a single parameter validation error."""
        tracker = FunctionCallingErrorTracker()

        result = tracker.track_error("test_tool", "Missing required parameter: user_id")

        assert result is False
        assert len(tracker.error_counts) == 1
        assert tracker.error_counts["test_tool:Missing required parameter: user_id"] == 1

    def test_track_error_parameter_validation_below_threshold(self):
        """Test tracking repeated identical errors below threshold."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=3)

        result1 = tracker.track_error("test_tool", "Missing required parameter: user_id")
        assert result1 is False

        result2 = tracker.track_error("test_tool", "Missing required parameter: user_id")
        assert result2 is False

        assert tracker.error_counts["test_tool:Missing required parameter: user_id"] == 2

    def test_track_error_circuit_breaker_triggers(self):
        """Test that circuit breaker triggers when the same tool+error repeats at threshold."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=3)

        error_message = "Missing required parameter: user_id"
        key = f"test_tool:{error_message}"

        result1 = tracker.track_error("test_tool", error_message)
        assert result1 is False

        result2 = tracker.track_error("test_tool", error_message)
        assert result2 is False

        result3 = tracker.track_error("test_tool", error_message)
        assert result3 is True

        assert tracker.error_counts[key] == 3

    def test_track_error_different_tools_tracked_separately(self):
        """Test that the same error on different tools is tracked separately."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=2)

        error_message = "Missing required parameter: user_id"

        result1 = tracker.track_error("tool1", error_message)
        assert result1 is False

        result2 = tracker.track_error("tool2", error_message)
        assert result2 is False

        result3 = tracker.track_error("tool1", error_message)
        assert result3 is True

        result4 = tracker.track_error("tool2", error_message)
        assert result4 is True

        assert tracker.error_counts[f"tool1:{error_message}"] == 2
        assert tracker.error_counts[f"tool2:{error_message}"] == 2

    def test_track_error_different_error_messages_tracked_separately(self):
        """Test that different error messages on the same tool are tracked independently."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=2)

        # Two different errors on the same tool — each has its own counter
        result1 = tracker.track_error("test_tool", "Missing required parameter: user_id")
        assert result1 is False

        result2 = tracker.track_error("test_tool", "Missing required parameter: email")
        assert result2 is False  # different error key, counter = 1, does not trigger

        assert len(tracker.error_counts) == 2
        assert tracker.error_counts["test_tool:Missing required parameter: user_id"] == 1
        assert tracker.error_counts["test_tool:Missing required parameter: email"] == 1

    def test_track_error_different_urls_do_not_trigger_circuit_breaker(self):
        """Test the core design: different URLs failing once each do not break the circuit."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=3)

        result1 = tracker.track_error("internal_web_fetch", "HTTP 404: Not Found for url1")
        assert result1 is False

        result2 = tracker.track_error("internal_web_fetch", "HTTP 404: Not Found for url2")
        assert result2 is False

        result3 = tracker.track_error("internal_web_fetch", "HTTP 404: Not Found for url3")
        assert result3 is False

        # Three different 404s — each tracked separately, none trips the breaker
        assert len(tracker.error_counts) == 3

    def test_track_error_same_url_triggers_circuit_breaker(self):
        """Test that the same URL failing repeatedly does trigger the circuit breaker."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=3)

        for _ in range(3):
            result = tracker.track_error("internal_web_fetch", "HTTP 404: Not Found for url1")

        assert result is True

    def test_get_error_summary(self):
        """Test getting error summary — keys are tool:message format."""
        tracker = FunctionCallingErrorTracker()

        tracker.track_error("tool1", "Missing required parameter: id")
        tracker.track_error("tool1", "Missing required parameter: id")
        tracker.track_error("tool2", "Missing required parameter: name")

        summary = tracker.get_error_summary()

        assert len(summary) == 2
        assert summary["tool1:Missing required parameter: id"] == 2
        assert summary["tool2:Missing required parameter: name"] == 1

        # Verify it's a copy (modifying summary doesn't affect tracker)
        summary["new_key"] = 999
        assert "new_key" not in tracker.error_counts

    def test_get_error_summary_empty(self):
        """Test getting error summary when no errors tracked."""
        tracker = FunctionCallingErrorTracker()

        summary = tracker.get_error_summary()

        assert summary == {}

    def test_reset(self):
        """Test resetting error tracking."""
        tracker = FunctionCallingErrorTracker()

        tracker.track_error("tool1", "Missing required parameter: id")
        tracker.track_error("tool1", "Missing required parameter: id")
        tracker.track_error("tool2", "Missing required parameter: name")

        assert len(tracker.error_counts) == 2

        tracker.reset()

        assert len(tracker.error_counts) == 0
        assert tracker.error_counts == {}

    def test_reset_then_track_new_errors(self):
        """Test that tracking works correctly after reset."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=2)

        error_message = "Missing required parameter: id"
        key = f"test_tool:{error_message}"

        tracker.track_error("test_tool", error_message)
        result = tracker.track_error("test_tool", error_message)
        assert result is True

        tracker.reset()

        result = tracker.track_error("test_tool", error_message)
        assert result is False
        assert tracker.error_counts[key] == 1

    def test_track_error_with_max_repeated_errors_one(self):
        """Test circuit breaker with max_repeated_errors=1."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=1)

        error_message = "Missing required parameter: user_id"
        result = tracker.track_error("test_tool", error_message)

        assert result is True
        assert tracker.error_counts[f"test_tool:{error_message}"] == 1

    def test_error_key_format(self):
        """Test that error keys use tool:message format (first 100 chars of message)."""
        tracker = FunctionCallingErrorTracker()

        tool_name = "my_tool"
        error_message = "Missing required parameter: test_param"
        expected_key = f"{tool_name}:{error_message[:100]}"

        tracker.track_error(tool_name, error_message)

        assert expected_key in tracker.error_counts

    def test_error_message_truncated_to_100_chars(self):
        """Test that error messages longer than 100 chars are truncated in the key."""
        tracker = FunctionCallingErrorTracker()

        long_message = "A" * 200
        tracker.track_error("tool", long_message)

        expected_key = f"tool:{'A' * 100}"
        assert expected_key in tracker.error_counts
        assert len(list(tracker.error_counts.keys())[0]) == len("tool:") + 100

    def test_multiple_errors_mixed_types(self):
        """Test that different error messages on the same tool are tracked separately."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=3)

        result1 = tracker.track_error("tool1", "Missing required parameter: id")
        assert result1 is False

        result2 = tracker.track_error("tool1", "Network timeout")
        assert result2 is False

        result3 = tracker.track_error("tool1", "Missing required parameter: id")
        assert result3 is False  # second occurrence of first error, count=2, threshold=3

        assert len(tracker.error_counts) == 2
        assert tracker.error_counts["tool1:Missing required parameter: id"] == 2
        assert tracker.error_counts["tool1:Network timeout"] == 1

    def test_case_sensitive_error_tracking(self):
        """Test that tool names are case-sensitive."""
        tracker = FunctionCallingErrorTracker()

        tracker.track_error("TestTool", "Missing required parameter: ID")
        tracker.track_error("testtool", "Missing required parameter: id")

        assert len(tracker.error_counts) == 2
        assert tracker.error_counts["TestTool:Missing required parameter: ID"] == 1
        assert tracker.error_counts["testtool:Missing required parameter: id"] == 1

    def test_circuit_breaker_continues_counting_after_trigger(self):
        """Test that errors continue to be counted after circuit breaker triggers."""
        tracker = FunctionCallingErrorTracker(max_repeated_errors=2)

        error_message = "Missing required parameter: user_id"
        key = f"test_tool:{error_message}"

        tracker.track_error("test_tool", error_message)
        result = tracker.track_error("test_tool", error_message)
        assert result is True

        result = tracker.track_error("test_tool", error_message)
        assert result is True

        assert tracker.error_counts[key] == 3
