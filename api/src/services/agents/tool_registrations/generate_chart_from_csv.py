"""Generate Chart from CSV/JSON Data - For Data Analysis Agent"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def generate_chart_from_data(
    data: str,
    chart_type: str,
    title: str,
    x_column: str | None = None,
    y_column: str | None = None,
    description: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a Chart.js visualization from CSV or JSON data.

    This tool is specifically for the Data Analysis Agent to create charts
    from uploaded files or analyzed data.

    Args:
        data: CSV text or JSON array string containing the data
        chart_type: Type of chart (bar, line, pie, doughnut, scatter, etc.)
        title: Chart title
        x_column: Column name for X-axis (required for bar, line, scatter)
        y_column: Column name for Y-axis (required for bar, line, scatter)
        description: Optional chart description
        config: Configuration dict (contains runtime context)

    Returns:
        Chart configuration dict with Chart.js format
    """
    try:
        import io

        import pandas as pd

        # Log incoming parameters for debugging
        logger.info(
            f"generate_chart_from_data called with chart_type='{chart_type}', title='{title}', x_column='{x_column}', y_column='{y_column}'"
        )

        # Validate chart_type
        if not chart_type or not isinstance(chart_type, str) or not chart_type.strip():
            return {"success": False, "error": "Chart type is required and must be a non-empty string"}

        # Parse data to DataFrame
        df = None

        # Try JSON first
        try:
            data_obj = json.loads(data)
            if isinstance(data_obj, list):
                df = pd.DataFrame(data_obj)
        except:
            pass

        # Try CSV if JSON failed
        if df is None:
            try:
                df = pd.read_csv(io.StringIO(data))
            except Exception as e:
                logger.error(f"Failed to parse data as CSV: {e}")
                return {"success": False, "error": "Could not parse data. Please provide valid CSV or JSON format."}

        if df is None or df.empty:
            return {"success": False, "error": "No data to visualize"}

        logger.info(f"Parsed data: {len(df)} rows, columns: {list(df.columns)}")

        # Prepare chart data based on type
        chart_config = {
            "chart_type": chart_type.lower(),  # Use chart_type to match ChartRenderer
            "library": "chartjs",  # Required by ChartRenderer
            "title": title,
            "description": description or "",
        }

        if chart_type.lower() in ["bar", "line", "scatter"]:
            # Need X and Y columns
            if not x_column or not y_column:
                return {
                    "success": False,
                    "error": f"Chart type '{chart_type}' requires x_column and y_column parameters",
                }

            if x_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Column '{x_column}' not found in data. Available: {list(df.columns)}",
                }

            if y_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Column '{y_column}' not found in data. Available: {list(df.columns)}",
                }

            # Extract labels and data
            labels = df[x_column].astype(str).tolist()
            values = df[y_column].tolist()

            chart_config["data"] = {
                "labels": labels,
                "datasets": [
                    {
                        "label": y_column,
                        "data": values,
                        "backgroundColor": "rgba(54, 162, 235, 0.5)",
                        "borderColor": "rgba(54, 162, 235, 1)",
                        "borderWidth": 2,
                    }
                ],
            }

        elif chart_type.lower() in ["pie", "doughnut"]:
            # For pie/doughnut, use first two columns or specified columns
            if x_column and y_column:
                if x_column not in df.columns or y_column not in df.columns:
                    return {"success": False, "error": f"Columns not found. Available: {list(df.columns)}"}
                labels = df[x_column].astype(str).tolist()
                values = df[y_column].tolist()
            else:
                # Use first two columns
                if len(df.columns) < 2:
                    return {"success": False, "error": "Need at least 2 columns for pie/doughnut chart"}
                labels = df.iloc[:, 0].astype(str).tolist()
                values = df.iloc[:, 1].tolist()

            # Generate colors
            colors = [f"rgba({(i * 50) % 255}, {(i * 100) % 255}, {(i * 150) % 255}, 0.6)" for i in range(len(labels))]

            chart_config["data"] = {
                "labels": labels,
                "datasets": [{"data": values, "backgroundColor": colors, "borderWidth": 1}],
            }
        else:
            return {"success": False, "error": f"Unsupported chart type: {chart_type}"}

        logger.info(f"Generated chart config: {chart_type} with {len(chart_config['data']['labels'])} data points")

        return {"success": True, "chart": chart_config, "message": f"Chart '{title}' generated successfully"}

    except Exception as e:
        logger.error(f"Error generating chart from data: {e}", exc_info=True)
        return {"success": False, "error": f"Chart generation failed: {str(e)}"}
