import sqlite3
import hashlib
from datetime import datetime
import os


class WBSEDCLDatabase:
    """Database handler for WBSEDCL Tracking System"""

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
            response = input("Do you want to recreate it? (yes/no): ")
            if response.lower() != 'yes':
                print("Database initialization cancelled.")
                return False
            os.remove(self.db_path)

        conn = self.connect()
        cursor = conn.cursor()

        try:
            with open(schema_file, 'r') as f:
                cursor.executescript(f.read())
            conn.commit()
            print("Database initialized successfully.")
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
                       department, designation, is_active, is_superuser
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
    # Users & roles
    # ------------------------------------------------------------------
    def create_user(self, username, password, full_name,
                    email=None, department=None, designation=None,
                    is_superuser=False, created_by=None):

        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users
                (username, password_hash, full_name, email,
                 department, designation, is_superuser, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                username,
                self.hash_password(password),
                full_name,
                email,
                department,
                designation,
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
        finally:
            self.close()

    # ------------------------------------------------------------------
    # Notesheets
    # ------------------------------------------------------------------
    def create_notesheet(self, data):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO notesheets
                (notesheet_number, subject, sender_name, sender_organization,
                 sender_address, reference_number, received_date, category,
                 priority, remarks, received_by, current_holder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                data["received_by"]
            ))

            notesheet_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO notesheet_movements
                (notesheet_id, to_user, forwarded_by, action_taken, comments)
                VALUES (?, ?, ?, 'Received', 'Initial receipt')
            """, (notesheet_id, data["received_by"], data["received_by"]))

            conn.commit()
            return notesheet_id

        except Exception:
            conn.rollback()
            return None
        finally:
            self.close()

    def forward_notesheet(self, movement):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO notesheet_movements
                (notesheet_id, from_user, to_user, forwarded_by,
                 action_taken, comments)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                movement["notesheet_id"],
                movement["from_user"],
                movement["to_user"],
                movement["forwarded_by"],
                movement["action_taken"],
                movement.get("comments")
            ))
            conn.commit()
            return True
        finally:
            self.close()

    # ------------------------------------------------------------------
    # Bills
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
                 priority, remarks, received_by, current_holder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                data["received_by"]
            ))

            bill_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO bill_movements
                (bill_id, to_user, forwarded_by, action_taken, comments)
                VALUES (?, ?, ?, 'Received', 'Initial receipt')
            """, (bill_id, data["received_by"], data["received_by"]))

            conn.commit()
            return bill_id

        except Exception:
            conn.rollback()
            return None
        finally:
            self.close()

    def forward_bill(self, movement):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO bill_movements
                (bill_id, from_user, to_user, forwarded_by,
                 action_taken, comments)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                movement["bill_id"],
                movement["from_user"],
                movement["to_user"],
                movement["forwarded_by"],
                movement["action_taken"],
                movement.get("comments")
            ))
            conn.commit()
            return True
        finally:
            self.close()

    # ------------------------------------------------------------------
    # ✅ FIXED LOG ACTIVITY (IMPORTANT)
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
        """
        Flexible activity logger.
        Works with all existing app.py calls.
        """

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
