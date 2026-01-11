import sqlite3
import hashlib
from datetime import datetime
import os


class WBSEDCLDatabase:
    """Database handler for WBSEDCL Tracking System with Section Support"""

    def __init__(self, db_path='wbsedcl_tracking.db'):
        self.db_path = db_path
        self.conn = None

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def initialize_database(self, schema_file='wbsedcl_schema.sql'):
        if os.path.exists(self.db_path):
            print(f"Database already exists at {self.db_path}")
            return False

        conn = self.connect()
        cursor = conn.cursor()

        try:
            with open(schema_file, 'r') as f:
                cursor.executescript(f.read())
            conn.commit()
            print(f"Database initialized successfully at {self.db_path}")
            return True
        except Exception as e:
            print(f"Error initializing database: {e}")
            conn.rollback()
            return False
        finally:
            self.close()

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate_user(self, username, password):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT user_id, username, full_name, email,
                       section_id, is_active, is_superuser
                FROM users
                WHERE username = ? AND password_hash = ?
            """, (username, self.hash_password(password)))

            user = cursor.fetchone()
            if user and user["is_active"]:
                cursor.execute("""
                    UPDATE users SET last_login = ?
                    WHERE user_id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user["user_id"]))
                conn.commit()
                return dict(user)

            return None
        finally:
            self.close()

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    def get_user_permissions(self, user_id):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM vw_user_permissions WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else {}
        finally:
            self.close()

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------
    def get_all_sections(self):
        """Get all sections"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM sections ORDER BY section_name')
            sections = cursor.fetchall()
            return [dict(row) for row in sections]
        finally:
            self.close()

    def get_section_users(self, section_id):
        """Get all users in a section"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT user_id, username, full_name, designation, 
                       is_section_head, sub_section_id
                FROM users
                WHERE section_id = ? AND is_active = 1
                ORDER BY is_section_head DESC, full_name
            ''', (section_id,))
            users = cursor.fetchall()
            return [dict(row) for row in users]
        finally:
            self.close()

    def get_receive_section_users(self):
        """Get all receive section users"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT DISTINCT u.user_id, u.username, u.full_name, u.designation
                FROM users u
                JOIN user_role_mapping urm ON u.user_id = urm.user_id
                JOIN user_roles ur ON urm.role_id = ur.role_id
                WHERE ur.role_name = 'receive_section' AND u.is_active = 1
                ORDER BY u.full_name
            ''')
            users = cursor.fetchall()
            return [dict(row) for row in users]
        finally:
            self.close()

    # ------------------------------------------------------------------
    # Users & roles
    # ------------------------------------------------------------------
    def create_user(self, username, password, full_name,
                    email=None, phone=None, section_id=None, 
                    sub_section_id=None, designation=None,
                    is_section_head=False, is_superuser=False, 
                    created_by=None):

        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users
                (username, password_hash, full_name, email, phone,
                 section_id, sub_section_id, designation, 
                 is_section_head, is_superuser, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                username,
                self.hash_password(password),
                full_name,
                email,
                phone,
                section_id,
                sub_section_id,
                designation,
                is_section_head,
                is_superuser,
                created_by
            ))

            conn.commit()
            return cursor.lastrowid

        except sqlite3.IntegrityError:
            return None
        finally:
            self.close()

    def assign_role(self, user_id, role_id, assigned_by):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO user_role_mapping (user_id, role_id, assigned_by)
                VALUES (?, ?, ?)
            """, (user_id, role_id, assigned_by))
            conn.commit()
            return True
        except:
            return False
        finally:
            self.close()

    # ------------------------------------------------------------------
    # Notesheets with Section Support
    # ------------------------------------------------------------------
    def create_notesheet(self, data):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO notesheets
                (notesheet_number, subject, sender_name, sender_organization,
                 sender_address, reference_number, received_date, category,
                 priority, remarks, received_by, current_holder,
                 current_section_id, current_sub_section_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["notesheet_number"],
                data["subject"],
                data["sender_name"],
                data.get("sender_organization"),
                data.get("sender_address"),
                data.get("reference_number"),
                data["received_date"],
                data.get("category"),
                data.get("priority", "Normal"),
                data.get("remarks"),
                data["received_by"],
                data["received_by"],
                data.get("current_section_id", 1),  # Default to Receive Section
                data.get("current_sub_section_id")
            ))

            notesheet_id = cursor.lastrowid

            # Get user's section
            cursor.execute('SELECT section_id, sub_section_id FROM users WHERE user_id = ?', 
                         (data["received_by"],))
            user_info = cursor.fetchone()

            # FIXED: Use received_date from form data for initial movement
            cursor.execute("""
                INSERT INTO notesheet_movements
                (notesheet_id, to_user, to_section_id, to_sub_section_id,
                 forwarded_by, forwarded_date, action_taken, comments)
                VALUES (?, ?, ?, ?, ?, ?, 'Received', 'Initial receipt')
            """, (notesheet_id, data["received_by"], 
                  user_info[0] if user_info else 1, 
                  user_info[1] if user_info else None,
                  data["received_by"],
                  data["received_date"]))  # ← FIXED: Use received_date from form

            conn.commit()
            return notesheet_id

        except Exception as e:
            print(f"Error creating notesheet: {e}")
            conn.rollback()
            return None
        finally:
            self.close()

    def forward_notesheet(self, movement):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            # Get from user's section info
            cursor.execute('SELECT section_id, sub_section_id FROM users WHERE user_id = ?',
                        (movement["from_user"],))
            from_info = cursor.fetchone()

            # Get to user's section info
            cursor.execute('SELECT section_id, sub_section_id FROM users WHERE user_id = ?',
                        (movement["to_user"],))
            to_info = cursor.fetchone()

            # Use custom forward date if provided, otherwise use current timestamp
            forward_date = movement.get("forward_date")
            if not forward_date:
                from datetime import datetime
                forward_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                # If only date provided, add time component
                if len(forward_date) == 10:  # YYYY-MM-DD format
                    from datetime import datetime
                    forward_date = forward_date + ' ' + datetime.now().strftime('%H:%M:%S')

            cursor.execute("""
                INSERT INTO notesheet_movements
                (notesheet_id, from_user, from_section_id, from_sub_section_id,
                to_user, to_section_id, to_sub_section_id,
                forwarded_by, forwarded_date, action_taken, comments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                movement["notesheet_id"],
                movement["from_user"],
                from_info[0] if from_info else None,
                from_info[1] if from_info else None,
                movement["to_user"],
                to_info[0] if to_info else None,
                to_info[1] if to_info else None,
                movement["forwarded_by"],
                forward_date,  # Use custom or current date
                movement["action_taken"],
                movement.get("comments")
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error forwarding notesheet: {e}")
            return False
        finally:
            self.close()

    def park_notesheet(self, notesheet_id, user_id, reason, comments=None):
        """Park a notesheet in Receive Section"""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE notesheets
                SET is_parked = 1,
                    park_reason = ?,
                    parked_date = ?,
                    parked_by = ?,
                    current_status = 'Parked'
                WHERE notesheet_id = ?
            """, (reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                  user_id, notesheet_id))

            cursor.execute("""
                INSERT INTO notesheet_movements
                (notesheet_id, to_user, forwarded_by, action_taken, comments)
                VALUES (?, ?, ?, 'Parked', ?)
            """, (notesheet_id, user_id, user_id, comments or reason))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error parking notesheet: {e}")
            return False
        finally:
            self.close()

    def unpark_notesheet(self, notesheet_id, user_id):
        """Unpark a notesheet"""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE notesheets
                SET is_parked = 0,
                    park_reason = NULL,
                    parked_date = NULL,
                    parked_by = NULL,
                    current_status = 'Received'
                WHERE notesheet_id = ?
            """, (notesheet_id,))

            cursor.execute("""
                INSERT INTO notesheet_movements
                (notesheet_id, to_user, forwarded_by, action_taken, comments)
                VALUES (?, ?, ?, 'Unparked', 'Document released from park')
            """, (notesheet_id, user_id, user_id))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error unparking notesheet: {e}")
            return False
        finally:
            self.close()

    # ------------------------------------------------------------------
    # Bills with Section Support
    # ------------------------------------------------------------------
    def create_bill(self, data):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO bills
                (bill_number, invoice_number, vendor_name, vendor_address,
                 vendor_gstin, vendor_pan, bill_date, received_date,
                 bill_amount, taxable_amount, gst_amount, tds_amount,
                 net_payable_amount, bill_type, category, description,
                 priority, remarks, received_by, current_holder,
                 current_section_id, current_sub_section_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["bill_number"],
                data.get("invoice_number"),
                data["vendor_name"],
                data.get("vendor_address"),
                data.get("vendor_gstin"),
                data.get("vendor_pan"),
                data.get("bill_date"),
                data.get("received_date"),
                data["bill_amount"],
                data.get("taxable_amount"),
                data.get("gst_amount"),
                data.get("tds_amount"),
                data.get("net_payable_amount"),
                data.get("bill_type"),
                data.get("category"),
                data.get("description"),
                data.get("priority", "Normal"),
                data.get("remarks"),
                data["received_by"],
                data["received_by"],
                data.get("current_section_id", 1),
                data.get("current_sub_section_id")
            ))

            bill_id = cursor.lastrowid

            # Get user's section
            cursor.execute('SELECT section_id, sub_section_id FROM users WHERE user_id = ?',
                         (data["received_by"],))
            user_info = cursor.fetchone()

            # FIXED: Use received_date from form data for initial movement
            cursor.execute("""
                INSERT INTO bill_movements
                (bill_id, to_user, to_section_id, to_sub_section_id,
                 forwarded_by, forwarded_date, action_taken, comments)
                VALUES (?, ?, ?, ?, ?, ?, 'Received', 'Initial receipt')
            """, (bill_id, data["received_by"],
                  user_info[0] if user_info else 1,
                  user_info[1] if user_info else None,
                  data["received_by"],
                  data.get("received_date")))  # ← FIXED: Use received_date from form

            conn.commit()
            return bill_id

        except Exception as e:
            print(f"Error creating bill: {e}")
            conn.rollback()
            return None
        finally:
            self.close()

    def forward_bill(self, movement):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            # Get from user's section info
            cursor.execute('SELECT section_id, sub_section_id FROM users WHERE user_id = ?',
                        (movement["from_user"],))
            from_info = cursor.fetchone()

            # Get to user's section info
            cursor.execute('SELECT section_id, sub_section_id FROM users WHERE user_id = ?',
                        (movement["to_user"],))
            to_info = cursor.fetchone()

            # Use custom forward date if provided, otherwise use current timestamp
            forward_date = movement.get("forward_date")
            if not forward_date:
                from datetime import datetime
                forward_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                # If only date provided, add time component
                if len(forward_date) == 10:  # YYYY-MM-DD format
                    from datetime import datetime
                    forward_date = forward_date + ' ' + datetime.now().strftime('%H:%M:%S')

            cursor.execute("""
                INSERT INTO bill_movements
                (bill_id, from_user, from_section_id, from_sub_section_id,
                to_user, to_section_id, to_sub_section_id,
                forwarded_by, forwarded_date, action_taken, comments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                movement["bill_id"],
                movement["from_user"],
                from_info[0] if from_info else None,
                from_info[1] if from_info else None,
                movement["to_user"],
                to_info[0] if to_info else None,
                to_info[1] if to_info else None,
                movement["forwarded_by"],
                forward_date,  # Use custom or current date
                movement["action_taken"],
                movement.get("comments")
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error forwarding bill: {e}")
            return False
        finally:
            self.close()

    # ------------------------------------------------------------------
    # Activity logging
    # ------------------------------------------------------------------
    def log_activity(
        self,
        user_id,
        activity_type,
        description,
        ip_address=None,
        entity_type=None,
        entity_id=None
    ):
        """Flexible activity logger"""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO activity_logs
                (user_id, activity_type, entity_type,
                 entity_id, description, ip_address, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                activity_type,
                entity_type,
                entity_id,
                description,
                ip_address,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))

            conn.commit()
            return True

        except Exception as e:
            print(f"Error logging activity: {e}")
            conn.rollback()
            return False

        finally:
            self.close()


# =============================================================================
# MAIN EXECUTION - Database Initialization Script
# =============================================================================

def main():
    """Initialize the database with default data"""
    print("=" * 60)
    print("WBSEDCL Tracking System - Database Initialization")
    print("=" * 60)
    
    db = WBSEDCLDatabase()
    
    # Initialize database from schema file
    if not db.initialize_database():
        print("Database initialization cancelled or failed.")
        return
    
    # Create default superuser
    print("\nDatabase initialized with default superuser:")
    print("Username: admin")
    print("Password: admin123")
    print("\nPlease change the default password immediately!")
    
    # Test authentication
    print("=" * 60)
    print("Testing authentication...")
    user = db.authenticate_user('admin', 'admin123')
    if user:
        print(f"✅ Authentication successful for: {user['full_name']}")
        perms = db.get_user_permissions(user['user_id'])
        print(f"✅ Permissions loaded: {perms.get('roles', 'N/A')}")
    else:
        print("❌ Authentication failed!")
    
    # Show sections
    print("=" * 60)
    print("Available Sections:")
    sections = db.get_all_sections()
    for section in sections:
        print(f"  {section['section_id']}. {section['section_name']} ({section['section_code']})")
    
    print("=" * 60)
    print("Database setup completed successfully!")
    print("=" * 60)
    print("\nYou can now run the application:")
    print("  python app.py")
    print("\nDefault login credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("=" * 60)


if __name__ == '__main__':
    main()