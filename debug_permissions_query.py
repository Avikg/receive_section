"""
Check and fix get_user_permissions query
"""

import sqlite3

conn = sqlite3.connect('wbsedcl_tracking.db')
cursor = conn.cursor()

print("=" * 80)
print("DEBUGGING get_user_permissions QUERY")
print("=" * 80)

# Simulate what get_user_permissions likely does
print("\n1. Testing likely query from init_database.py:")
cursor.execute('''
    SELECT 
        u.user_id,
        u.username,
        u.full_name,
        u.section_id,
        s.section_name,
        u.sub_section_id,
        ss.sub_section_name,
        COALESCE(MAX(ur.is_section_head), 0) as is_section_head,
        u.is_superuser,
        COALESCE(MAX(ur.can_receive), 0) as can_receive,
        COALESCE(MAX(ur.can_forward), 0) as can_forward,
        COALESCE(MAX(ur.can_approve), 0) as can_approve,
        COALESCE(MAX(ur.can_manage_users), 0) as can_manage_users,
        COALESCE(MAX(ur.can_edit_any), 0) as can_edit_any,
        GROUP_CONCAT(ur.role_name) as roles
    FROM users u
    LEFT JOIN sections s ON u.section_id = s.section_id
    LEFT JOIN sub_sections ss ON u.sub_section_id = ss.sub_section_id
    LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
    LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
    WHERE u.user_id = ?
    GROUP BY u.user_id
''', (4,))

result = cursor.fetchone()
columns = [desc[0] for desc in cursor.description]
perms = dict(zip(columns, result))

print("\nResult with MAX aggregation:")
for key, value in perms.items():
    print(f"   {key} = {value}")

# Now check what's actually in user_roles for section_head
print("\n2. Checking user_roles table for section_head:")
cursor.execute("SELECT * FROM user_roles WHERE role_name = 'section_head'")
role = cursor.fetchone()
cursor.execute("PRAGMA table_info(user_roles)")
cols = [c[1] for c in cursor.fetchall()]
role_dict = dict(zip(cols, role))

print("   Section_head role values:")
for key, value in role_dict.items():
    if key.startswith('can_') or key == 'is_section_head':
        print(f"      {key} = {value}")

# Check if column has the right value
print("\n3. Direct query on user_roles:")
cursor.execute('''
    SELECT ur.is_section_head 
    FROM user_role_mapping urm
    JOIN user_roles ur ON urm.role_id = ur.role_id
    WHERE urm.user_id = 4 AND ur.role_name = 'section_head'
''')
direct = cursor.fetchone()
print(f"   is_section_head from user_roles for DCC = {direct[0] if direct else 'NULL'}")

conn.close()

print("\n" + "=" * 80)
print("DIAGNOSIS:")
print("If is_section_head = 0 above but = 1 in direct query,")
print("then the MAX() aggregation or GROUP BY is the problem.")
print("=" * 80)