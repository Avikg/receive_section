"""
Add System User (ID=0) for tracking failed logins with unknown usernames
"""

import sqlite3

conn = sqlite3.connect('wbsedcl_tracking.db')
cursor = conn.cursor()

try:
    # Check if user_id = 0 exists
    cursor.execute('SELECT user_id FROM users WHERE user_id = 0')
    existing = cursor.fetchone()
    
    if existing:
        print("✅ System user (ID=0) already exists")
    else:
        print("Creating system user (ID=0)...")
        
        # Insert system user with ID = 0
        cursor.execute('''
            INSERT INTO users (
                user_id, username, password_hash, full_name, 
                email, phone, section_id, designation, 
                is_active, is_superuser, created_at
            ) VALUES (
                0, 'system', 'SYSTEM_NO_PASSWORD', 'System', 
                NULL, NULL, NULL, 'System Account',
                0, 0, datetime('now')
            )
        ''')
        
        conn.commit()
        print("✅ System user created successfully!")
        print("\n   User ID: 0")
        print("   Username: system")
        print("   Full Name: System")
        print("   Purpose: Track failed logins with unknown usernames")
        
    # Show current system user
    cursor.execute('SELECT user_id, username, full_name, is_active FROM users WHERE user_id = 0')
    user = cursor.fetchone()
    
    print("\nCurrent System User:")
    print(f"  ID: {user[0]}")
    print(f"  Username: {user[1]}")
    print(f"  Full Name: {user[2]}")
    print(f"  Active: {user[3]}")
    
    print("\n" + "="*80)
    print("Now failed login attempts with unknown usernames will be logged!")
    print("They will appear in Activity Logs with 'System' as the user.")
    print("="*80)
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()

finally:
    conn.close()