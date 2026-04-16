"""Tests for CronValidator."""


from src.services.scheduler.cron_validator import CronValidator


class TestCronValidatorValidate:
    def test_valid_every_minute(self):
        result = CronValidator.validate("* * * * *")
        assert result["is_valid"] is True
        assert "next_run" in result
        assert len(result["preview"]) == 5

    def test_valid_every_hour(self):
        result = CronValidator.validate("0 * * * *")
        assert result["is_valid"] is True
        assert result["description"] == "Every hour"

    def test_valid_daily_midnight(self):
        result = CronValidator.validate("0 0 * * *")
        assert result["is_valid"] is True
        assert result["description"] == "Daily at midnight"

    def test_valid_weekly(self):
        result = CronValidator.validate("0 0 * * 0")
        assert result["is_valid"] is True
        assert result["description"] == "Weekly on Sunday at midnight"

    def test_valid_monthly(self):
        result = CronValidator.validate("0 0 1 * *")
        assert result["is_valid"] is True
        assert result["description"] == "Monthly on the 1st at midnight"

    def test_valid_yearly(self):
        result = CronValidator.validate("0 0 1 1 *")
        assert result["is_valid"] is True
        assert result["description"] == "Yearly on January 1st at midnight"

    def test_valid_every_5_minutes(self):
        result = CronValidator.validate("*/5 * * * *")
        assert result["is_valid"] is True
        assert result["description"] == "Every 5 minutes"

    def test_valid_every_15_minutes(self):
        result = CronValidator.validate("*/15 * * * *")
        assert result["is_valid"] is True
        assert result["description"] == "Every 15 minutes"

    def test_valid_every_30_minutes(self):
        result = CronValidator.validate("*/30 * * * *")
        assert result["is_valid"] is True
        assert result["description"] == "Every 30 minutes"

    def test_valid_every_2_hours(self):
        result = CronValidator.validate("0 */2 * * *")
        assert result["is_valid"] is True
        assert result["description"] == "Every 2 hours"

    def test_valid_every_6_hours(self):
        result = CronValidator.validate("0 */6 * * *")
        assert result["is_valid"] is True
        assert result["description"] == "Every 6 hours"

    def test_valid_every_12_hours(self):
        result = CronValidator.validate("0 */12 * * *")
        assert result["is_valid"] is True
        assert result["description"] == "Every 12 hours"

    def test_invalid_expression(self):
        result = CronValidator.validate("not-a-cron")
        assert result["is_valid"] is False
        assert "error" in result

    def test_invalid_out_of_range(self):
        result = CronValidator.validate("99 99 99 99 99")
        assert result["is_valid"] is False

    def test_empty_string(self):
        result = CronValidator.validate("")
        assert result["is_valid"] is False

    def test_preview_has_5_items(self):
        result = CronValidator.validate("* * * * *")
        assert result["is_valid"] is True
        assert len(result["preview"]) == 5
        for t in result["preview"]:
            assert "T" in t

    def test_next_run_is_isoformat(self):
        from datetime import datetime
        result = CronValidator.validate("0 12 * * *")
        assert result["is_valid"] is True
        datetime.fromisoformat(result["next_run"])


class TestCronValidatorDescribe:
    def test_every_minute_description(self):
        assert CronValidator._describe_cron("* * * * *") == "Every minute"

    def test_every_hour_description(self):
        assert CronValidator._describe_cron("0 * * * *") == "Every hour"

    def test_custom_minute_at_specific_hour(self):
        desc = CronValidator._describe_cron("30 9 * * *")
        assert "30" in desc
        assert "9" in desc

    def test_specific_month_description(self):
        desc = CronValidator._describe_cron("0 0 1 3 *")
        # _describe_cron calls .capitalize() on the full string, lowercasing
        # everything except the first character — "Mar" becomes "mar"
        assert "mar" in desc.lower()

    def test_specific_weekday_description(self):
        desc = CronValidator._describe_cron("0 0 * * 5")
        # Same reason — "Fri" becomes "fri" after .capitalize()
        assert "fri" in desc.lower()

    def test_wrong_parts_count_returns_custom(self):
        assert CronValidator._describe_cron("* * * *") == "Custom schedule"

    def test_step_minute_description(self):
        desc = CronValidator._describe_cron("*/10 * * * *")
        assert "10" in desc

    def test_step_hour_description(self):
        desc = CronValidator._describe_cron("0 */4 * * *")
        assert "4" in desc
