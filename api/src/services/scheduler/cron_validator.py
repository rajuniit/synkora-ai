"""
Cron expression validator
"""

import logging
from datetime import datetime
from typing import Any

from croniter import croniter

logger = logging.getLogger(__name__)


class CronValidator:
    """Validates cron expressions"""

    @staticmethod
    def validate(cron_expression: str) -> dict[str, Any]:
        """
        Validate a cron expression

        Args:
            cron_expression: The cron expression to validate

        Returns:
            Dict containing validation results
        """
        try:
            # Check if the cron expression is valid
            if not croniter.is_valid(cron_expression):
                return {"is_valid": False, "error": "Invalid cron expression format"}

            # Try to get the next execution time
            base_time = datetime.now()
            cron = croniter(cron_expression, base_time)
            next_run = cron.get_next(datetime)

            # Get the next few execution times for preview
            preview_times = []
            cron = croniter(cron_expression, base_time)
            for _ in range(5):
                preview_times.append(cron.get_next(datetime).isoformat())

            return {
                "is_valid": True,
                "next_run": next_run.isoformat(),
                "preview": preview_times,
                "description": CronValidator._describe_cron(cron_expression),
            }

        except Exception as e:
            logger.warning(f"Error validating cron expression: {str(e)}")
            return {"is_valid": False, "error": str(e)}

    @staticmethod
    def _describe_cron(cron_expression: str) -> str:
        """
        Generate a human-readable description of a cron expression

        Args:
            cron_expression: The cron expression to describe

        Returns:
            Human-readable description
        """
        parts = cron_expression.split()

        if len(parts) != 5:
            return "Custom schedule"

        minute, hour, day, month, weekday = parts

        # Common patterns
        if cron_expression == "* * * * *":
            return "Every minute"
        elif cron_expression == "0 * * * *":
            return "Every hour"
        elif cron_expression == "0 0 * * *":
            return "Daily at midnight"
        elif cron_expression == "0 0 * * 0":
            return "Weekly on Sunday at midnight"
        elif cron_expression == "0 0 1 * *":
            return "Monthly on the 1st at midnight"
        elif cron_expression == "0 0 1 1 *":
            return "Yearly on January 1st at midnight"
        elif cron_expression == "*/5 * * * *":
            return "Every 5 minutes"
        elif cron_expression == "*/15 * * * *":
            return "Every 15 minutes"
        elif cron_expression == "*/30 * * * *":
            return "Every 30 minutes"
        elif cron_expression == "0 */2 * * *":
            return "Every 2 hours"
        elif cron_expression == "0 */6 * * *":
            return "Every 6 hours"
        elif cron_expression == "0 */12 * * *":
            return "Every 12 hours"

        # Build description from parts
        description_parts = []

        # Minute
        if minute == "*":
            description_parts.append("every minute")
        elif minute.startswith("*/"):
            description_parts.append(f"every {minute[2:]} minutes")
        else:
            description_parts.append(f"at minute {minute}")

        # Hour
        if hour != "*":
            if hour.startswith("*/"):
                description_parts.append(f"every {hour[2:]} hours")
            else:
                description_parts.append(f"at hour {hour}")

        # Day
        if day != "*":
            if day.startswith("*/"):
                description_parts.append(f"every {day[2:]} days")
            else:
                description_parts.append(f"on day {day}")

        # Month
        if month != "*":
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            try:
                month_idx = int(month) - 1
                if 0 <= month_idx < 12:
                    description_parts.append(f"in {months[month_idx]}")
            except ValueError:
                description_parts.append(f"in month {month}")

        # Weekday
        if weekday != "*":
            weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            try:
                weekday_idx = int(weekday)
                if 0 <= weekday_idx < 7:
                    description_parts.append(f"on {weekdays[weekday_idx]}")
            except ValueError:
                description_parts.append(f"on weekday {weekday}")

        return " ".join(description_parts).capitalize()
