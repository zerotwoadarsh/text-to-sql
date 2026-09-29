from sqlalchemy import create_engine, inspect

engine = create_engine("sqlite:///chinook.db")
inspector = inspect(engine)

_cached_schema = None

def get_schema_context() -> str:
    global _cached_schema
    table_names = inspector.get_table_names()
    schema_parts = []

    for table_name in table_names:
        columns = inspector.get_columns(table_name)
        fks = inspector.get_foreign_keys(table_name)

        # for columns
        column_lines = []
        for col in columns:
            line = f"  - {col['name']} ({col['type']})"
            column_lines.append(line)

        #for foreign keys
        fk_lines = []
        for fk in fks:
            constrained = ", ".join(fk["constrained_columns"])
            referred_table = fk["referred_table"]
            referred_cols = ", ".join(fk["referred_columns"])
            fk_lines.append(f"  - {constrained} -> {referred_table}({referred_cols})")

        table_block = f"Table: {table_name}\nColumns:\n" + "\n".join(column_lines)
        if fk_lines:
            table_block += "\nForeign Keys:\n" + "\n".join(fk_lines)

        schema_parts.append(table_block)

    _cached_schema = "\n\n".join(schema_parts)
    return "\n\n".join(schema_parts)


if __name__ == "__main__":
    schema_text = get_schema_context()
    print(schema_text)
    print("\n\n--- Character count:", len(schema_text), "---")