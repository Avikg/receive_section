"""
Add is_section_head column to user_roles table
"""

import sqlite3

conn = sqlite3.connect('wbsedcl_tracking.db')
cursor = conn.cursor()

print("=" * 80)
print("ADDING is_section_head COLUMN TO user_roles TABLE")
print("=" * 80)

try:
    # Add the column
    print("\n1. Adding is_section_head column...")
    cursor.execute("ALTER TABLE user_roles ADD COLUMN is_section_head INTEGER DEFAULT 0")
    print("   ✓ Column added!")
    
    # Update section_head role to have is_section_head = 1
    print("\n2. Setting is_section_head = 1 for section_head role...")
    cursor.execute("UPDATE user_roles SET is_section_head = 1 WHERE role_name = 'section_head'")
    print("   ✓ Updated section_head role!")
    
    # Update superuser to also have is_section_head = 1
    print("\n3. Setting is_section_head = 1 for superuser role...")
    cursor.execute("UPDATE user_roles SET is_section_head = 1 WHERE role_name = 'superuser'")
    print("   ✓ Updated superuser role!")
    
    conn.commit()
    
    # Verify
    print("\n4. Verification - user_roles after update:")
    cursor.execute("SELECT role_id, role_name, can_receive, can_forward, can_approve, is_section_head FROM user_roles")
    print("   ID | Role Name        | Receive | Forward | Approve | Section Head")
    print("   " + "-" * 70)
    for row in cursor.fetchall():
        print(f"   {row[0]:2d} | {row[1]:16s} | {row[2]:7d} | {row[3]:7d} | {row[4]:7d} | {row[5]:12d}")
    
    print("\n✅ SUCCESS! is_section_head column added and configured!")
    print("\nNow restart Flask and test with DCC user!")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("\n⚠️  Column already exists! Updating values...")
        cursor.execute("UPDATE user_roles SET is_section_head = 1 WHERE role_name = 'section_head'")
        cursor.execute("UPDATE user_roles SET is_section_head = 1 WHERE role_name = 'superuser'")
        conn.commit()
        print("✓ Values updated!")
    else:
        print(f"\n❌ Error: {e}")

conn.close()
print("=" * 80)