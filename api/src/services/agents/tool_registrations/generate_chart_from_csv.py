"""Generate Chart from CSV/JSON Data - For Data Analysis Agent"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Formula injection prefixes that are dangerous in spreadsheet apps
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _safe_label(value: Any) -> Any:
    """Prefix spreadsheet formula triggers so they render as plain text."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


# Chart types rendered by Chart.js (existing)
CHARTJS_TYPES = {"bar", "line", "pie", "doughnut", "scatter"}

# Chart types rendered by Recharts (installed, zero extra deps)
RECHARTS_TYPES = {"area", "stacked_bar", "radar", "treemap", "funnel"}

# Chart types rendered by Plotly (react-plotly.js)
PLOTLY_TYPES = {"heatmap", "box", "box_plot", "violin", "candlestick", "waterfall"}


def _build_table_data(df, max_rows: int = 50) -> list[dict]:
    """Return first max_rows as a list of plain dicts for the inline data table."""
    return df.head(max_rows).astype(object).where(df.head(max_rows).notna(), None).to_dict(orient="records")


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
    Generate a visualization from CSV or JSON data.

    Supports Chart.js (bar, line, pie, doughnut, scatter),
    Recharts (area, stacked_bar, radar, treemap, funnel),
    and Plotly (heatmap, box, violin, candlestick, waterfall).

    Args:
        data: CSV text or JSON array string containing the data
        chart_type: Type of chart to generate
        title: Chart title
        x_column: Column name for X-axis
        y_column: Column name for Y-axis
        description: Optional chart description
        config: Configuration dict (contains runtime context)

    Returns:
        Chart configuration dict
    """
    try:
        import io

        import pandas as pd

        logger.info(
            f"generate_chart_from_data called with chart_type='{chart_type}', title='{title}', "
            f"x_column='{x_column}', y_column='{y_column}'"
        )

        if not chart_type or not isinstance(chart_type, str) or not chart_type.strip():
            return {"success": False, "error": "Chart type is required and must be a non-empty string"}

        chart_type = chart_type.lower().strip()

        # Parse data to DataFrame
        df = None
        try:
            data_obj = json.loads(data)
            if isinstance(data_obj, list):
                df = pd.DataFrame(data_obj)
        except Exception:
            pass

        if df is None:
            try:
                df = pd.read_csv(io.StringIO(data))
            except Exception as e:
                logger.error(f"Failed to parse data as CSV: {e}")
                return {"success": False, "error": "Could not parse data. Please provide valid CSV or JSON format."}

        if df is None or df.empty:
            return {"success": False, "error": "No data to visualize"}

        logger.info(f"Parsed data: {len(df)} rows, columns: {list(df.columns)}")

        table_data = _build_table_data(df)

        # ------------------------------------------------------------------ #
        # Chart.js chart types                                                 #
        # ------------------------------------------------------------------ #
        if chart_type in CHARTJS_TYPES:
            chart_config: dict[str, Any] = {
                "chart_type": chart_type,
                "library": "chartjs",
                "title": title,
                "description": description or "",
                "table_data": table_data,
            }

            if chart_type in ("bar", "line", "scatter"):
                if not x_column or not y_column:
                    return {
                        "success": False,
                        "error": f"Chart type '{chart_type}' requires x_column and y_column parameters",
                    }
                if x_column not in df.columns:
                    return {"success": False, "error": f"Column '{x_column}' not found. Available: {list(df.columns)}"}
                if y_column not in df.columns:
                    return {"success": False, "error": f"Column '{y_column}' not found. Available: {list(df.columns)}"}

                labels = [_safe_label(v) for v in df[x_column].astype(str).tolist()]
                values = df[y_column].tolist()
                chart_config["data"] = {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": _safe_label(y_column),
                            "data": values,
                            "backgroundColor": "rgba(99, 102, 241, 0.5)",
                            "borderColor": "rgba(99, 102, 241, 1)",
                            "borderWidth": 2,
                        }
                    ],
                }

            elif chart_type in ("pie", "doughnut"):
                if x_column and y_column:
                    if x_column not in df.columns or y_column not in df.columns:
                        return {"success": False, "error": f"Columns not found. Available: {list(df.columns)}"}
                    labels = [_safe_label(v) for v in df[x_column].astype(str).tolist()]
                    values = df[y_column].tolist()
                else:
                    if len(df.columns) < 2:
                        return {"success": False, "error": "Need at least 2 columns for pie/doughnut chart"}
                    labels = [_safe_label(v) for v in df.iloc[:, 0].astype(str).tolist()]
                    values = df.iloc[:, 1].tolist()

                palette = [
                    "#6366f1",
                    "#8b5cf6",
                    "#06b6d4",
                    "#10b981",
                    "#f59e0b",
                    "#ef4444",
                    "#ec4899",
                    "#84cc16",
                ]
                colors = [palette[i % len(palette)] for i in range(len(labels))]
                chart_config["data"] = {
                    "labels": labels,
                    "datasets": [{"data": values, "backgroundColor": colors, "borderWidth": 1}],
                }

            logger.info(f"Generated chartjs config: {chart_type}")
            return {"success": True, "chart": chart_config, "message": f"Chart '{title}' generated successfully"}

        # ------------------------------------------------------------------ #
        # Recharts chart types                                                 #
        # ------------------------------------------------------------------ #
        if chart_type in RECHARTS_TYPES:
            chart_config = {
                "chart_type": chart_type,
                "library": "recharts",
                "title": title,
                "description": description or "",
                "table_data": table_data,
            }

            if chart_type == "area":
                if not x_column or not y_column:
                    return {"success": False, "error": "area chart requires x_column and y_column"}
                if x_column not in df.columns or y_column not in df.columns:
                    return {"success": False, "error": f"Columns not found. Available: {list(df.columns)}"}
                area_df = df[[x_column, y_column]].copy()
                area_df[y_column] = pd.to_numeric(area_df[y_column], errors="coerce")
                chart_config["data"] = {
                    "data": area_df.rename(columns={x_column: "name", y_column: "value"}).to_dict(orient="records"),
                    "xKey": "name",
                    "yKey": "value",
                }

            elif chart_type == "stacked_bar":
                if not x_column:
                    return {"success": False, "error": "stacked_bar requires x_column"}
                if x_column not in df.columns:
                    return {"success": False, "error": f"Column '{x_column}' not found. Available: {list(df.columns)}"}
                numeric_cols = [c for c in df.select_dtypes(include="number").columns if c != x_column]
                if not numeric_cols:
                    return {"success": False, "error": "No numeric columns found for stacking"}
                series_cols = numeric_cols if not y_column else [y_column]
                keep = [x_column] + series_cols
                chart_config["data"] = {
                    "data": df[keep].rename(columns={x_column: "name"}).to_dict(orient="records"),
                    "xKey": "name",
                    "series": series_cols,
                }

            elif chart_type == "radar":
                if not x_column or not y_column:
                    return {"success": False, "error": "radar chart requires x_column and y_column"}
                if x_column not in df.columns or y_column not in df.columns:
                    return {"success": False, "error": f"Columns not found. Available: {list(df.columns)}"}
                chart_config["data"] = {
                    "data": df[[x_column, y_column]]
                    .rename(columns={x_column: "subject", y_column: "value"})
                    .to_dict(orient="records"),
                    "xKey": "subject",
                    "yKey": "value",
                }

            elif chart_type == "treemap":
                if not x_column or not y_column:
                    return {"success": False, "error": "treemap requires x_column (name) and y_column (size)"}
                if x_column not in df.columns or y_column not in df.columns:
                    return {"success": False, "error": f"Columns not found. Available: {list(df.columns)}"}
                chart_config["data"] = {
                    "data": df[[x_column, y_column]]
                    .rename(columns={x_column: "name", y_column: "size"})
                    .to_dict(orient="records"),
                    "xKey": "name",
                    "yKey": "size",
                }

            elif chart_type == "funnel":
                if not x_column or not y_column:
                    return {"success": False, "error": "funnel requires x_column (stage) and y_column (value)"}
                if x_column not in df.columns or y_column not in df.columns:
                    return {"success": False, "error": f"Columns not found. Available: {list(df.columns)}"}
                chart_config["data"] = {
                    "data": df[[x_column, y_column]]
                    .sort_values(y_column, ascending=False)
                    .rename(columns={x_column: "name", y_column: "value"})
                    .to_dict(orient="records"),
                    "xKey": "name",
                    "yKey": "value",
                }

            logger.info(f"Generated recharts config: {chart_type}")
            return {"success": True, "chart": chart_config, "message": f"Chart '{title}' generated successfully"}

        # ------------------------------------------------------------------ #
        # Plotly chart types                                                   #
        # ------------------------------------------------------------------ #
        if chart_type in PLOTLY_TYPES:
            chart_config = {
                "chart_type": chart_type,
                "library": "plotly",
                "title": title,
                "description": description or "",
                "table_data": table_data,
            }

            numeric_cols = df.select_dtypes(include="number").columns.tolist()

            if chart_type == "heatmap":
                # Build correlation matrix or use provided x/y columns
                if x_column and y_column and x_column in df.columns and y_column in df.columns:
                    # Pivot table: x_column as columns, y_column as rows, first numeric as values
                    value_col = next((c for c in numeric_cols if c not in (x_column, y_column)), None)
                    if value_col:
                        pivot = df.pivot_table(index=y_column, columns=x_column, values=value_col, aggfunc="mean")
                        z = pivot.values.tolist()
                        x_labels = [str(c) for c in pivot.columns]
                        y_labels = [str(r) for r in pivot.index]
                    else:
                        return {"success": False, "error": "heatmap needs a numeric value column"}
                elif len(numeric_cols) >= 2:
                    # Correlation matrix
                    corr = df[numeric_cols].corr()
                    z = corr.values.tolist()
                    x_labels = numeric_cols
                    y_labels = numeric_cols
                else:
                    return {"success": False, "error": "heatmap requires numeric columns or x_column/y_column"}

                chart_config["data"] = {
                    "data": [{"type": "heatmap", "z": z, "x": x_labels, "y": y_labels, "colorscale": "Blues"}],
                    "layout": {"title": ""},
                }

            elif chart_type in ("box", "box_plot"):
                target_cols = [y_column] if y_column and y_column in df.columns else numeric_cols[:6]
                traces = [{"type": "box", "y": df[col].dropna().tolist(), "name": col} for col in target_cols]
                chart_config["data"] = {"data": traces, "layout": {"showlegend": False}}
                chart_config["chart_type"] = "box"

            elif chart_type == "violin":
                target_cols = [y_column] if y_column and y_column in df.columns else numeric_cols[:6]
                traces = [
                    {"type": "violin", "y": df[col].dropna().tolist(), "name": col, "box": {"visible": True}}
                    for col in target_cols
                ]
                chart_config["data"] = {"data": traces, "layout": {"showlegend": False}}

            elif chart_type == "candlestick":
                needed = {"open", "high", "low", "close"}
                cols_lower = {c.lower(): c for c in df.columns}
                if not needed.issubset(cols_lower.keys()):
                    return {
                        "success": False,
                        "error": "candlestick requires columns: open, high, low, close",
                    }
                date_col = (
                    x_column
                    if x_column and x_column in df.columns
                    else (next((c for c in df.columns if "date" in c.lower() or "time" in c.lower()), None))
                )
                trace: dict[str, Any] = {
                    "type": "candlestick",
                    "open": df[cols_lower["open"]].tolist(),
                    "high": df[cols_lower["high"]].tolist(),
                    "low": df[cols_lower["low"]].tolist(),
                    "close": df[cols_lower["close"]].tolist(),
                }
                if date_col:
                    trace["x"] = df[date_col].astype(str).tolist()
                chart_config["data"] = {"data": [trace], "layout": {"xaxis": {"type": "category"}}}

            elif chart_type == "waterfall":
                if not x_column or not y_column:
                    return {"success": False, "error": "waterfall requires x_column (labels) and y_column (values)"}
                if x_column not in df.columns or y_column not in df.columns:
                    return {"success": False, "error": f"Columns not found. Available: {list(df.columns)}"}
                labels = df[x_column].astype(str).tolist()
                values = pd.to_numeric(df[y_column], errors="coerce").fillna(0).tolist()
                chart_config["data"] = {
                    "data": [
                        {
                            "type": "waterfall",
                            "x": labels,
                            "y": values,
                            "connector": {"line": {"color": "rgb(63, 63, 63)"}},
                        }
                    ],
                    "layout": {},
                }

            logger.info(f"Generated plotly config: {chart_type}")
            return {"success": True, "chart": chart_config, "message": f"Chart '{title}' generated successfully"}

        return {
            "success": False,
            "error": f"Unsupported chart type: {chart_type}. Supported: "
            f"{', '.join(sorted(CHARTJS_TYPES | RECHARTS_TYPES | PLOTLY_TYPES))}",
        }

    except Exception as e:
        logger.error(f"Error generating chart from data: {e}", exc_info=True)
        return {"success": False, "error": f"Chart generation failed: {str(e)}"}
