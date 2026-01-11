"""
Check Database Schema
"""

import sqlite3

conn = sqlite3.connect('wbsedcl_tracking.db')
cursor = conn.cursor()

print("=" * 80)
print("DATABASE SCHEMA CHECK")
print("=" * 80)

# List all tables
print("\n1. All tables in database:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
for table in tables:
    print(f"   - {table[0]}")

# Check user_roles table structure
print("\n2. user_roles table:")
cursor.execute("PRAGMA table_info(user_roles)")
for col in cursor.fetchall():
    print(f"   Column: {col[1]} ({col[2]})")

# Check what's in user_roles
print("\n3. Roles in user_roles table:")
cursor.execute("SELECT * FROM user_roles")
for row in cursor.fetchall():
    print(f"   {row}")

# Check user_role_mapping
print("\n4. User role mappings for DCC user:")
cursor.execute('''
    SELECT urm.*, ur.role_name 
    FROM user_role_mapping urm
    JOIN user_roles ur ON urm.role_id = ur.role_id
    WHERE urm.user_id = 4
''')
for row in cursor.fetchall():
    print(f"   {row}")

conn.close()
print("=" * 80)