import re

def is_date_string(val) -> bool:
    """Helper to check if a value is formatted like a date or month."""
    if not isinstance(val, str):
        return False
    # Matches YYYY-MM-DD or YYYY-MM
    if re.match(r"^\d{4}-\d{2}(-\d{2})?$", val):
        return True
    # Matches MM-YYYY or MM/YYYY
    if re.match(r"^\d{2}[-/]\d{4}$", val):
        return True
    # Matches month names
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
              "january", "february", "march", "april", "june", "july", "august", "september", "october", "november", "december"]
    if val.lower() in months:
        return True
    return False

from backend.services.schema_service import is_identifier_column

def determine_chart_config(columns: list, rows: list) -> dict:
    """
    Analyzes the query result set to select the optimal chart type and axes.
    Returns: {
        "chart_type": str,  # 'line' | 'bar' | 'donut' | 'scatter' | 'none'
        "x_axis": str | None,
        "y_axis": str | None,
        "data": list
    }
    """
    if not rows or not columns:
        return {"chart_type": "none", "x_axis": None, "y_axis": None, "data": []}

    # Inspect first row to guess column types
    first_row = rows[0]
    
    date_cols = []
    numeric_cols = []
    text_cols = []
    
    # We want to identify the types of all columns
    for col in columns:
        val = first_row.get(col)
        if val is None:
            # Check other rows if the first row has None
            for r in rows[1:10]:
                if r.get(col) is not None:
                    val = r.get(col)
                    break
        
        # Determine data type
        if is_date_string(val):
            date_cols.append(col)
        elif isinstance(val, (int, float)) and not isinstance(val, bool):
            # Exclude identifiers from numeric metrics for charting
            if is_identifier_column(col):
                text_cols.append(col)
            else:
                numeric_cols.append(col)
        else:
            text_cols.append(col)

    # Visualization selection heuristics:
    
    # 1. Date/Time X-axis + Numeric Y-axis -> Line Chart
    if date_cols and numeric_cols:
        return {
            "chart_type": "line",
            "x_axis": date_cols[0],
            "y_axis": numeric_cols[0],
            "data": rows
        }
        
    # 2. Text X-axis + Numeric Y-axis
    if text_cols and numeric_cols:
        x_col = text_cols[0]
        y_col = numeric_cols[0]
        
        # Count unique values in X column to decide between Donut and Bar
        unique_vals = set(str(r.get(x_col, "")) for r in rows)
        
        if len(unique_vals) <= 5 and len(unique_vals) > 1:
            return {
                "chart_type": "donut",
                "x_axis": x_col,
                "y_axis": y_col,
                "data": rows
            }
        else:
            return {
                "chart_type": "bar",
                "x_axis": x_col,
                "y_axis": y_col,
                "data": rows
            }

    # 3. Two Numeric columns (and no text/date) -> Scatter Plot
    if len(numeric_cols) >= 2:
        return {
            "chart_type": "scatter",
            "x_axis": numeric_cols[0],
            "y_axis": numeric_cols[1],
            "data": rows
        }

    # 4. Single numeric column (no category, no date) -> Bar chart
    if numeric_cols:
        # Create an artificial X axis or use index
        # Let's map it as x_axis=index
        chart_data = []
        for i, r in enumerate(rows):
            new_r = r.copy()
            new_r["__index__"] = f"Item {i+1}"
            chart_data.append(new_r)
            
        return {
            "chart_type": "bar",
            "x_axis": "__index__",
            "y_axis": numeric_cols[0],
            "data": chart_data
        }

    # 5. Otherwise, no suitable chart (fallback to table rendering)
    return {
        "chart_type": "none",
        "x_axis": None,
        "y_axis": None,
        "data": []
    }
