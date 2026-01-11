"""
Fix Section Head Permissions
This script adds missing permissions for section_head role
"""

import sqlite3

conn = sqlite3.connect('wbsedcl_tracking.db')
cursor = conn.cursor()

print("=" * 80)
print("FIXING SECTION HEAD PERMISSIONS")
print("=" * 80)

# Check current permissions for section_head role (role_id = 3)
print("\n1. Current permissions for section_head role:")
cursor.execute('''
    SELECT permission_name, value 
    FROM user_permissions 
    WHERE role_id = 3
''')
current = cursor.fetchall()
if current:
    for row in current:
        print(f"   {row[0]} = {row[1]}")
else:
    print("   NO PERMISSIONS FOUND!")

# Add missing permissions
print("\n2. Adding required permissions...")

permissions = [
    (3, 'is_section_head', 1),
    (3, 'can_forward', 1),
    (3, 'can_approve', 1),
    (3, 'can_receive', 0)
]

for role_id, perm_name, value in permissions:
    cursor.execute('''
        INSERT OR REPLACE INTO user_permissions (role_id, permission_name, value)
        VALUES (?, ?, ?)
    ''', (role_id, perm_name, value))
    print(f"   ✓ Set {perm_name} = {value} for role_id {role_id}")

conn.commit()

# Verify
print("\n3. Permissions after fix:")
cursor.execute('''
    SELECT permission_name, value 
    FROM user_permissions 
    WHERE role_id = 3
''')
for row in cursor.fetchall():
    print(f"   {row[0]} = {row[1]}")

conn.close()

print("\n✅ DONE! Section head permissions fixed.")
print("=" * 80)
print("\nNow restart Flask and login as DCC user to test!")