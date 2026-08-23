import os
import re
from google import genai
from backend.config import settings
from backend.services.sql_service import get_db_schema
from backend.utils.sql_validator import is_safe_sql

# Configure Gemini API using new google-genai SDK
API_KEY = settings.GEMINI_API_KEY
client = None
if API_KEY:
    client = genai.Client(api_key=API_KEY)

# Simple in-memory session manager for chat history
# session_id -> list of dicts: [{"question": str, "sql": str, "summary": str}]
chat_history = {}

def get_history_context(session_id: str) -> str:
    """Formats previous Q&A context for the system prompt."""
    if not session_id or session_id not in chat_history:
        return "No previous context."
    
    exchanges = chat_history[session_id]
    context_lines = []
    for i, ex in enumerate(exchanges[-3:]):  # Keep last 3 exchanges to avoid context bloating
        context_lines.append(f"Exchange {i+1}:")
        context_lines.append(f"  User Question: {ex['question']}")
        context_lines.append(f"  Generated SQL: {ex['sql']}")
        context_lines.append(f"  AI Summary: {ex['summary']}")
    return "\n".join(context_lines)

def add_history_context(session_id: str, question: str, sql: str, summary: str):
    """Saves a successful Q&A exchange to history."""
    if not session_id:
        return
    if session_id not in chat_history:
        chat_history[session_id] = []
    chat_history[session_id].append({
        "question": question,
        "sql": sql,
        "summary": summary
    })

def format_schema() -> str:
    """Formats the SQLite database schema for the system prompt."""
    schema = get_db_schema()
    schema_lines = []
    for table_name, columns in schema.items():
        schema_lines.append(f"Table: {table_name}")
        for col in columns:
            schema_lines.append(f"  - {col['name']} ({col['type']})")
    return "\n".join(schema_lines)

def clean_generated_sql(sql_text: str) -> str:
    """Extracts raw SQL from Markdown code blocks if present."""
    # Match ```sql ... ```
    match = re.search(r"```sql(.*?)```", sql_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Match ``` ... ```
    match = re.search(r"```(.*?)```", sql_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return sql_text.strip()

def generate_sql(question: str, session_id: str = "default_session", max_retries: int = 2) -> str:
    """
    Asks Gemini to translate a natural language question into SQL.
    Includes database schema and previous conversation context.
    Performs validation and retries if the validation fails.
    """
    if not API_KEY:
        raise ValueError("Gemini API key is missing. Please set the GEMINI_API_KEY environment variable in your .env file.")

    schema_text = format_schema()
    context_text = get_history_context(session_id)

    system_prompt = f"""You are an expert SQL engineer. Your task is to translate natural language business questions into clean, valid, and safe SQLite SQL queries.

You must only use the tables and columns defined in the schema below:

{schema_text}

Rules for SQL generation:
1. Only generate read-only SELECT and WITH statements. Do not generate INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, or other database-modifying commands.
2. The database dialect is SQLite. Ensure all functions used are valid SQLite functions (e.g. use strftime for dates or group-by functions appropriately).
3. Do not include any explanation or markdown formatting other than the SQL itself inside a ```sql ... ``` code block.
4. Keep the queries optimal and use aliases where helpful (e.g. SUM(revenue) AS total_revenue).
5. If the user question references date ranges, months, or years, map them to order_date (formatted as 'YYYY-MM-DD').
   - example: 'March' refers to order_date between '2025-03-01' and '2025-03-31' (or appropriate year). Note that the data dates are in 2025 (since generating scripts use start_date = Jan 1, 2025).
6. For monthly calculations, you can use strftime('%m', order_date) or strftime('%Y-%m', order_date).
7. If the user asks a follow-up question (e.g. "What about profit?", "Show details for North"), use the context of previous exchanges provided below to infer missing tables/filters.

Previous context:
{context_text}
"""

    current_prompt = f"User Question: {question}\n\nGenerate the SQLite query:"
    
    retries = 0
    feedback = ""
    
    while retries <= max_retries:
        prompt_with_feedback = current_prompt
        if feedback:
            prompt_with_feedback += f"\n\nCorrection Feedback:\n{feedback}"
            
        # Call the new SDK Client
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[system_prompt, prompt_with_feedback]
        )
        
        generated_text = response.text
        sql = clean_generated_sql(generated_text)
        
        # Validate the generated SQL
        is_safe, err_msg = is_safe_sql(sql)
        if is_safe:
            return sql
        
        # If unsafe, increment retry count and provide feedback to Gemini
        feedback = f"The query you generated was rejected for safety reasons: {err_msg}. Please regenerate a safe read-only SELECT or WITH statement."
        retries += 1
        
    raise ValueError("Failed to generate a safe SQL query after multiple attempts. Please rephrase your question.")

def generate_insights(question: str, sql: str, columns: list, rows: list) -> dict:
    """
    Asks Gemini to analyze the query results and generate business insights:
    Executive Summary, Key Findings, Business Impact, and Recommendations.
    """
    if not API_KEY:
        return {
            "summary": "AI Insights are unavailable because the Gemini API key is missing.",
            "key_findings": ["Please set GEMINI_API_KEY in your .env file to enable insights."],
            "business_impact": "Missing API configuration.",
            "recommendations": ["Add GEMINI_API_KEY environment variable."]
        }

    # Format the data results as a text table for Gemini
    if not rows:
        results_text = "No records found matching the query."
    else:
        # Show first 30 rows in the prompt to prevent bloating the token count
        results_text = f"Columns: {', '.join(columns)}\n"
        for i, row in enumerate(rows[:30]):
            row_vals = [str(row.get(col, "")) for col in columns]
            results_text += f"Row {i+1}: {', '.join(row_vals)}\n"
        if len(rows) > 30:
            results_text += f"... (showing 30 of {len(rows)} total rows)"

    system_prompt = f"""You are a senior AI business analyst. Analyze the following SQL query, its output, and the user's question, and generate a professional, executive-grade business analysis.

User Question: {question}
Executed SQL: {sql}
Query Results:
{results_text}

Please generate the response structured EXACTLY in the following markdown format:

### EXECUTIVE SUMMARY
[Provide a concise 1-2 sentence executive summary of the findings here]

### KEY FINDINGS
- [Key finding 1 with specific numbers/metrics from the data]
- [Key finding 2 with specific numbers/metrics from the data]
- [Key finding 3 with specific numbers/metrics from the data]

### BUSINESS IMPACT
[Explain the business impact of these findings. Connect the data to business outcomes.]

### RECOMMENDED ACTIONS
- [Actionable, specific business recommendation 1 based on the findings]
- [Actionable, specific business recommendation 2 based on the findings]
- [Actionable, specific business recommendation 3 based on the findings]

Instructions:
1. Never fabricate or hallucinate numbers. Use only the exact numbers returned in the query results.
2. Clearly distinguish between facts directly supported by the data and qualitative business explanations/hypotheses.
3. Be professional, concise, and business-focused.
"""

    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=system_prompt
    )
    response_text = response.text

    # Parse the structured response
    summary = "No executive summary generated."
    key_findings = []
    business_impact = "No business impact generated."
    recommendations = []

    try:
        # Parse Executive Summary
        summary_match = re.search(r"### EXECUTIVE SUMMARY\s*(.*?)\s*(?=###|$)", response_text, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary = summary_match.group(1).strip()

        # Parse Key Findings
        findings_match = re.search(r"### KEY FINDINGS\s*(.*?)\s*(?=###|$)", response_text, re.DOTALL | re.IGNORECASE)
        if findings_match:
            findings_block = findings_match.group(1).strip()
            # Split by markdown bullets
            key_findings = [line.strip("- *").strip() for line in findings_block.split("\n") if line.strip().startswith(("-", "*"))]
        
        # Parse Business Impact
        impact_match = re.search(r"### BUSINESS IMPACT\s*(.*?)\s*(?=###|$)", response_text, re.DOTALL | re.IGNORECASE)
        if impact_match:
            business_impact = impact_match.group(1).strip()

        # Parse Recommendations
        rec_match = re.search(r"### RECOMMENDED ACTIONS\s*(.*?)\s*(?=###|$)", response_text, re.DOTALL | re.IGNORECASE)
        if rec_match:
            rec_block = rec_match.group(1).strip()
            recommendations = [line.strip("- *").strip() for line in rec_block.split("\n") if line.strip().startswith(("-", "*"))]

    except Exception as e:
        # Fallback if parsing fails
        summary = response_text
        key_findings = ["Failed to parse findings structure."]
        business_impact = "Parsing error occurred."
        recommendations = ["Check generated insights text."]

    return {
        "summary": summary,
        "key_findings": key_findings if key_findings else ["No specific findings parsed."],
        "business_impact": business_impact,
        "recommendations": recommendations if recommendations else ["No specific recommendations parsed."]
    }
