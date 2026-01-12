"""
Add session_id column to activity_logs table for session tracking
"""

import sqlite3

conn = sqlite3.connect('wbsedcl_tracking.db')
cursor = conn.cursor()

try:
    # Check if session_id column exists
    cursor.execute("PRAGMA table_info(activity_logs)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'session_id' in columns:
        print("✅ session_id column already exists")
    else:
        print("Adding session_id column to activity_logs...")
        
        cursor.execute('''
            ALTER TABLE activity_logs 
            ADD COLUMN session_id TEXT
        ''')
        
        conn.commit()
        print("✅ session_id column added successfully!")
    
    # Show updated schema
    print("\nUpdated activity_logs schema:")
    cursor.execute("PRAGMA table_info(activity_logs)")
    for col in cursor.fetchall():
        print(f"  {col[1]} ({col[2]}) - NOT NULL: {col[3]}")
    
    print("\n" + "="*80)
    print("Session tracking is now enabled!")
    print("All activities during a user session will be grouped together.")
    print("="*80)
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()

finally:
    conn.close()