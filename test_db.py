import sqlite3

conn = sqlite3.connect("chinook.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables found:", tables)
conn.close()