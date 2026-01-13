"""
Add Letters Module to WBSEDCL Tracking System
Run this script to add letters and letter_movements tables
Usage: python add_letters_tables.py
"""

import sqlite3
from datetime import datetime

def add_letters_tables():
    """Add letters and letter_movements tables to database"""
    
    try:
        conn = sqlite3.connect('wbsedcl_tracking.db')
        cursor = conn.cursor()
        
        print("=" * 60)
        print("Adding Letters Module to Database")
        print("=" * 60)
        
        # Create letters table (similar to notesheets/bills)
        print("\n1. Creating letters table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS letters (
                letter_id INTEGER PRIMARY KEY AUTOINCREMENT,
                letter_number TEXT NOT NULL UNIQUE,
                subject TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                sender_organization TEXT,
                sender_address TEXT,
                sender_email TEXT,
                sender_phone TEXT,
                reference_number TEXT,
                letter_date DATE,
                received_date DATE NOT NULL,
                category TEXT,
                priority TEXT DEFAULT 'Normal' CHECK(priority IN ('Urgent', 'High', 'Normal', 'Low')),
                letter_type TEXT CHECK(letter_type IN ('Incoming', 'Outgoing', 'Internal')),
                current_status TEXT DEFAULT 'Pending' CHECK(current_status IN ('Pending', 'Under Review', 'Replied', 'Closed', 'Archived')),
                current_holder INTEGER,
                current_section_id INTEGER,
                current_sub_section_id INTEGER,
                remarks TEXT,
                is_parked INTEGER DEFAULT 0,
                parked_by INTEGER,
                parked_date DATETIME,
                parked_reason TEXT,
                parked_comments TEXT,
                reply_required INTEGER DEFAULT 0,
                reply_deadline DATE,
                replied_date DATE,
                reply_reference TEXT,
                received_by INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (current_holder) REFERENCES users(user_id),
                FOREIGN KEY (current_section_id) REFERENCES sections(section_id),
                FOREIGN KEY (current_sub_section_id) REFERENCES sub_sections(sub_section_id),
                FOREIGN KEY (parked_by) REFERENCES users(user_id),
                FOREIGN KEY (received_by) REFERENCES users(user_id)
            )
        ''')
        print("   ✓ letters table created")
        
        # Create letter_movements table
        print("\n2. Creating letter_movements table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS letter_movements (
                movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                letter_id INTEGER NOT NULL,
                from_user INTEGER,
                to_user INTEGER NOT NULL,
                from_section_id INTEGER,
                to_section_id INTEGER,
                from_sub_section_id INTEGER,
                to_sub_section_id INTEGER,
                forwarded_by INTEGER NOT NULL,
                forwarded_date DATETIME NOT NULL,
                action_taken TEXT DEFAULT 'Forwarded',
                comments TEXT,
                is_current INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (letter_id) REFERENCES letters(letter_id) ON DELETE CASCADE,
                FOREIGN KEY (from_user) REFERENCES users(user_id),
                FOREIGN KEY (to_user) REFERENCES users(user_id),
                FOREIGN KEY (from_section_id) REFERENCES sections(section_id),
                FOREIGN KEY (to_section_id) REFERENCES sections(section_id),
                FOREIGN KEY (from_sub_section_id) REFERENCES sub_sections(sub_section_id),
                FOREIGN KEY (to_sub_section_id) REFERENCES sub_sections(sub_section_id),
                FOREIGN KEY (forwarded_by) REFERENCES users(user_id)
            )
        ''')
        print("   ✓ letter_movements table created")
        
        # Create indexes for better performance
        print("\n3. Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_letters_current_holder ON letters(current_holder)')
        print("   ✓ idx_letters_current_holder")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_letters_section ON letters(current_section_id)')
        print("   ✓ idx_letters_section")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_letters_status ON letters(current_status)')
        print("   ✓ idx_letters_status")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_letters_received_date ON letters(received_date)')
        print("   ✓ idx_letters_received_date")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_letter_movements_letter ON letter_movements(letter_id)')
        print("   ✓ idx_letter_movements_letter")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_letter_movements_current ON letter_movements(is_current)')
        print("   ✓ idx_letter_movements_current")
        
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Letters module added successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Copy letter routes to app.py")
        print("2. Create letter templates in templates/letters/")
        print("3. Update navigation menu in base.html")
        print("4. Update dashboard statistics")
        print("5. Restart Flask application")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure wbsedcl_tracking.db exists in the current directory")
        return False

if __name__ == '__main__':
    add_letters_tables()