"""
Check activity_logs table structure
"""

import sqlite3

conn = sqlite3.connect('wbsedcl_tracking.db')
cursor = conn.cursor()

print("=" * 80)
print("ACTIVITY_LOGS TABLE STRUCTURE")
print("=" * 80)

# Get table structure
cursor.execute("PRAGMA table_info(activity_logs)")
columns = cursor.fetchall()

print("\nColumns:")
for col in columns:
    print(f"  {col[1]} ({col[2]}) - PK: {col[5]}, NOT NULL: {col[3]}")

# Get sample data
print("\n" + "=" * 80)
print("SAMPLE DATA (First 5 rows)")
print("=" * 80)

cursor.execute("SELECT * FROM activity_logs LIMIT 5")
rows = cursor.fetchall()

if rows:
    # Get column names
    col_names = [desc[0] for desc in cursor.description]
    print("\nColumn names:", col_names)
    
    print("\nData:")
    for row in rows:
        print(row)
else:
    print("\nNo data in activity_logs table")

conn.close()
print("\n" + "=" * 80)