import re

# Blocked SQL command keywords (case-insensitive whole words)
BLOCKED_KEYWORDS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bPRAGMA\b"
]

def clean_sql(sql: str) -> str:
    """Remove comments and leading/trailing whitespace from the SQL query."""
    # Remove single-line comments (-- comment)
    sql_clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    # Remove multi-line comments (/* comment */)
    sql_clean = re.sub(r"/\*.*?\*/", "", sql_clean, flags=re.DOTALL)
    return sql_clean.strip()

def is_safe_sql(sql: str) -> tuple[bool, str]:
    """
    Validates if a SQL query is read-only and contains no prohibited keywords.
    Returns: (is_safe, error_message)
    """
    cleaned = clean_sql(sql)
    if not cleaned:
        return False, "SQL query is empty."

    # Check for blocked keywords
    for keyword in BLOCKED_KEYWORDS:
        if re.search(keyword, cleaned, re.IGNORECASE):
            # Exception for functions that contain the word (like REPLACE as a string function)
            # But raw REPLACE or other modifications should be blocked
            matched_word = re.findall(keyword, cleaned, re.IGNORECASE)
            return False, f"Blocked SQL command or keyword detected: '{matched_word[0]}'. Only read-only operations (SELECT, WITH) are allowed."

    # Split to get the first word
    words = cleaned.split()
    if not words:
        return False, "SQL query contains no commands."
        
    first_word = words[0].upper()
    # Normalize if it starts with brackets or parenthesis
    first_word = re.sub(r"[^A-Z]", "", first_word)

    if first_word not in ("SELECT", "WITH"):
        return False, f"Query started with '{first_word}'. Only SELECT or WITH queries are permitted."

    return True, ""
