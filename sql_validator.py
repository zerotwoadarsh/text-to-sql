import sqlglot
from sqlglot import exp

def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validates that the SQL is a single, safe SELECT statement.
    Returns (is_valid, cleaned_sql_or_error_message).
    """
    cleaned = sql.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("sql\n", "", 1).strip()

    try:
        all_statements = sqlglot.parse(cleaned, read="sqlite")
    except Exception as e:
        return False, f"SQL failed to parse: {e}"

    all_statements = [s for s in all_statements if s is not None]

    if len(all_statements) != 1:
        return False, f"Expected exactly 1 SQL statement, found {len(all_statements)}."

    parsed = all_statements[0]

    if not isinstance(parsed, exp.Select):
        return False, f"Only SELECT statements are allowed. Got: {type(parsed).__name__}"

    return True, cleaned


if __name__ == "__main__":
    test_cases = [
        "SELECT COUNT(*) FROM Customer;",
        "```sql\nSELECT * FROM Customer;\n```",
        "DROP TABLE Customer;",
        "DELETE FROM Customer WHERE CustomerId = 1;",
        "SELECT * FROM Customer; DROP TABLE Customer;",
    ]

    for sql in test_cases:
        is_valid, result = validate_sql(sql)
        print(f"Input: {sql!r}")
        print(f"  Valid: {is_valid} | Result: {result}")
        print()