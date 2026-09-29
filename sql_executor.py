import sqlite3
import pandas as pd

from sql_validator import validate_sql

DB_PATH = "chinook.db"
MAX_ROWS = 1000

def execute_sql(sql: str) -> dict:
    """
    Validates and executes a SQL query against the database in read-only mode.
    Returns a dict with keys: success (bool), data (DataFrame or None), error (str or None).
    """
    is_valid, result = validate_sql(sql)
    if not is_valid:
        return {"success": False, "data": None, "error": result}

    clean_sql = result

    try:
        
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        df = pd.read_sql_query(clean_sql, conn)
        conn.close()

        if len(df) > MAX_ROWS:
            df = df.head(MAX_ROWS)

        return {"success": True, "data": df, "error": None}

    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}


if __name__ == "__main__":
    test_queries = [
        "SELECT COUNT(*) FROM Customer;",
        "SELECT * FROM Customer LIMIT 3;",
        "SELECT * FROM NonExistentTable;",   
        "SELECT Name FORM Track;",            
    ]

    for sql in test_queries:
        print(f"\nQuery: {sql}")
        result = execute_sql(sql)
        if result["success"]:
            print("Success! Data:")
            print(result["data"])
        else:
            print("Failed. Error:", result["error"])