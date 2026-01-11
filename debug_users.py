import sqlite3

# Connect to database
conn = sqlite3.connect('wbsedcl_tracking.db')
cursor = conn.cursor()

print("=" * 60)
print("DATABASE DEBUG - USER AND ROLE INFORMATION")
print("=" * 60)

# Check all users
print("\n1. ALL USERS:")
cursor.execute('''
    SELECT u.user_id, u.username, u.full_name, u.section_id, s.section_name, u.is_active, u.is_superuser
    FROM users u
    LEFT JOIN sections s ON u.section_id = s.section_id
    ORDER BY u.user_id
''')
for row in cursor.fetchall():
    print(f"   ID:{row[0]:<3} Username:{row[1]:<15} Name:{row[2]:<20} Section_ID:{row[3]:<3} Section:{row[4] or 'N/A':<20} Active:{row[5]} Super:{row[6]}")

# Check user role mappings
print("\n2. USER ROLE MAPPINGS:")
cursor.execute('''
    SELECT urm.user_id, u.username, urm.role_id, ur.role_name
    FROM user_role_mapping urm
    JOIN users u ON urm.user_id = u.user_id
    JOIN user_roles ur ON urm.role_id = ur.role_id
    ORDER BY urm.user_id
''')
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"   User_ID:{row[0]:<3} Username:{row[1]:<15} Role_ID:{row[2]:<3} Role:{row[3]}")
else:
    print("   NO ROLE MAPPINGS FOUND!")

# Check current user (DCC - ID 4)
print("\n3. DCC USER DETAILS (ID=4):")
cursor.execute('''
    SELECT u.user_id, u.username, u.section_id, s.section_name
    FROM users u
    LEFT JOIN sections s ON u.section_id = s.section_id
    WHERE u.user_id = 4
''')
row = cursor.fetchone()
if row:
    dcc_section_id = row[2]
    print(f"   DCC: ID={row[0]}, Username={row[1]}, Section_ID={row[2]}, Section={row[3]}")
    
    # Now run the actual query that should return users
    print(f"\n4. TESTING QUERY - Users DCC should see (Section_ID={dcc_section_id}):")
    cursor.execute('''
        SELECT DISTINCT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
        FROM users u
        LEFT JOIN sections s ON u.section_id = s.section_id
        LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
        LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
        WHERE u.is_active = 1 
        AND u.user_id != 4
        AND u.is_superuser = 0
        AND (
            u.section_id = ?
            OR
            ur.role_name = 'section_head'
            OR
            ur.role_name = 'receive_section'
        )
        ORDER BY s.section_name, u.full_name
    ''', (dcc_section_id,))
    
    results = cursor.fetchall()
    if results:
        print(f"   Found {len(results)} users:")
        for row in results:
            print(f"      ID:{row[0]:<3} Name:{row[1]:<20} Designation:{row[2] or 'N/A':<15} Section:{row[3]}")
    else:
        print("   NO USERS RETURNED BY QUERY!")
        
        # Try simpler query
        print("\n5. SIMPLER TEST - Just same section users:")
        cursor.execute('''
            SELECT u.user_id, u.full_name, s.section_name, u.is_active, u.is_superuser
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            WHERE u.section_id = ?
            AND u.user_id != 4
        ''', (dcc_section_id,))
        simple_results = cursor.fetchall()
        if simple_results:
            print(f"   Found {len(simple_results)} users in same section:")
            for row in simple_results:
                print(f"      ID:{row[0]:<3} Name:{row[1]:<20} Section:{row[2]:<20} Active:{row[3]} Super:{row[4]}")
        else:
            print("   NO USERS IN SAME SECTION!")

conn.close()
print("\n" + "=" * 60)