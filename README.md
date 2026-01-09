# WBSEDCL Internal Tracking System - Database Documentation

## Overview
SQLite3 database system for tracking Notesheets and Bills with role-based access control and receive section functionality.

## Database Files
- `wbsedcl_schema.sql` - Complete database schema with tables, indexes, views, and triggers
- `init_database.py` - Python script to initialize and manage the database
- `wbsedcl_tracking.db` - SQLite database file (created after initialization)

## Quick Start

### 1. Initialize Database
```bash
python init_database.py
```

This will:
- Create the SQLite database
- Set up all tables, indexes, views, and triggers
- Create default user roles
- Create default superuser (username: `admin`, password: `admin123`)

### 2. Default Superuser Credentials
```
Username: admin
Password: admin123
```
**⚠️ IMPORTANT: Change the default password immediately after first login!**

## Database Schema

### 1. User Management Tables

#### `users`
Stores all user information.
- `user_id` - Primary key
- `username` - Unique username
- `password_hash` - Hashed password (SHA-256, use bcrypt in production)
- `full_name` - User's full name
- `email` - Email address
- `phone` - Contact number
- `department` - Department name
- `designation` - Job designation
- `is_active` - Active status (1=active, 0=inactive)
- `is_superuser` - Superuser flag
- `created_by` - User who created this account
- `created_at`, `updated_at`, `last_login` - Timestamps

#### `user_roles`
Defines available roles in the system.
- `role_id` - Primary key
- `role_name` - Unique role name
- `role_description` - Description of the role
- `can_receive` - Permission to receive documents
- `can_forward` - Permission to forward documents
- `can_approve` - Permission to approve documents
- `can_manage_users` - Permission to manage users

**Default Roles:**
1. **superuser** - Full system access
2. **receive_section** - Can receive and forward (2 users minimum)
3. **department_head** - Can approve and forward
4. **clerk** - Can forward only
5. **accounts_officer** - Can process and approve bills
6. **viewer** - Read-only access

#### `user_role_mapping`
Maps users to roles (many-to-many relationship).
- `mapping_id` - Primary key
- `user_id` - Reference to users table
- `role_id` - Reference to user_roles table
- `assigned_by` - User who assigned the role
- `assigned_at` - Assignment timestamp
- `is_active` - Active status of the role assignment

### 2. Notesheet Management Tables

#### `notesheets`
Main table for notesheet records.
- `notesheet_id` - Primary key
- `notesheet_number` - Unique notesheet number
- `subject` - Subject of the notesheet
- `reference_number` - External reference number
- `sender_name` - Name of sender
- `sender_organization` - Sender's organization
- `sender_address` - Sender's address
- `received_date` - Date when received
- `received_by` - User who received it
- `priority` - Low, Normal, High, Urgent
- `category` - Document category
- `current_status` - Received, In-Progress, Forwarded, Closed, Archived
- `current_holder` - User currently holding the notesheet
- `remarks` - Additional remarks
- `is_archived` - Archive status

#### `notesheet_movements`
Tracks all movements/forwarding of notesheets.
- `movement_id` - Primary key
- `notesheet_id` - Reference to notesheets table
- `from_user` - User who sent it
- `to_user` - User who received it
- `forwarded_by` - User who performed the forwarding
- `forwarded_date` - Timestamp of forwarding
- `action_taken` - Forwarded, Returned, Approved, Rejected
- `comments` - Comments/notes about the movement
- `expected_return_date` - Expected return date
- `is_current` - Flag for current movement (auto-managed by trigger)

#### `notesheet_attachments`
Stores file attachments for notesheets.
- `attachment_id` - Primary key
- `notesheet_id` - Reference to notesheets table
- `file_name` - Original file name
- `file_path` - Path to stored file
- `file_type` - MIME type
- `file_size` - File size in bytes
- `uploaded_by` - User who uploaded
- `uploaded_at` - Upload timestamp
- `description` - File description

### 3. Bills Management Tables

#### `bills`
Main table for bill records.
- `bill_id` - Primary key
- `bill_number` - Unique bill number
- `invoice_number` - Invoice number
- `vendor_name` - Vendor/supplier name
- `vendor_address` - Vendor address
- `vendor_gstin` - GST identification number
- `vendor_pan` - PAN number
- `bill_date` - Date on the bill
- `received_date` - Date when received
- `received_by` - User who received it
- `bill_amount` - Total bill amount
- `taxable_amount` - Taxable amount
- `gst_amount` - GST amount
- `tds_amount` - TDS amount
- `net_payable_amount` - Net amount payable
- `bill_type` - Purchase, Service, Maintenance, etc.
- `category` - Bill category
- `description` - Bill description
- `priority` - Low, Normal, High, Urgent
- `current_status` - Received, Under Verification, Approved, Payment Pending, Paid, Rejected
- `current_holder` - User currently holding the bill
- `payment_status` - Pending, Processed, Paid, Cancelled
- `payment_date` - Date of payment
- `payment_reference` - Payment reference number
- `is_archived` - Archive status
- `remarks` - Additional remarks

#### `bill_movements`
Tracks all movements/forwarding of bills.
- `movement_id` - Primary key
- `bill_id` - Reference to bills table
- `from_user` - User who sent it
- `to_user` - User who received it
- `forwarded_by` - User who performed the forwarding
- `forwarded_date` - Timestamp of forwarding
- `action_taken` - Forwarded, Verified, Approved, Rejected, Returned
- `comments` - Comments/notes about the movement
- `expected_return_date` - Expected return date
- `is_current` - Flag for current movement (auto-managed by trigger)

#### `bill_attachments`
Stores file attachments for bills.
- `attachment_id` - Primary key
- `bill_id` - Reference to bills table
- `file_name` - Original file name
- `file_path` - Path to stored file
- `file_type` - MIME type
- `file_size` - File size in bytes
- `uploaded_by` - User who uploaded
- `uploaded_at` - Upload timestamp
- `description` - File description

### 4. Audit Tables

#### `activity_logs`
Comprehensive activity logging.
- `log_id` - Primary key
- `user_id` - User who performed the action
- `activity_type` - Login, Logout, Create, Update, Delete, Forward
- `entity_type` - Notesheet, Bill, User
- `entity_id` - ID of the affected entity
- `description` - Description of the activity
- `ip_address` - IP address of the user
- `created_at` - Timestamp

## Database Views

### `vw_current_notesheets`
Shows all active (non-archived) notesheets with current holder information.

### `vw_current_bills`
Shows all active (non-archived) bills with current holder information.

### `vw_receive_section_users`
Lists all active users with receive_section role.

### `vw_user_permissions`
Aggregates all permissions for each user based on their assigned roles.

## Triggers

### Automatic Timestamp Updates
- `trg_notesheets_update` - Updates `updated_at` when notesheet is modified
- `trg_bills_update` - Updates `updated_at` when bill is modified
- `trg_users_update` - Updates `updated_at` when user is modified

### Movement Management
- `trg_notesheet_movement_insert` - Automatically manages current movement flag and updates current_holder
- `trg_bill_movement_insert` - Automatically manages current movement flag and updates current_holder

## Python Database Helper Functions

### User Management
```python
db = WBSEDCLDatabase()

# Create user
user_id = db.create_user(
    username='john_doe',
    password='secure_password',
    full_name='John Doe',
    email='john@wbsedcl.in',
    department='Engineering',
    designation='Engineer',
    created_by=1  # admin user_id
)

# Assign role
db.assign_role(user_id, 'receive_section', assigned_by=1)

# Remove role
db.remove_role(user_id, 'receive_section')

# Authenticate user
user = db.authenticate_user('john_doe', 'secure_password')

# Get user permissions
permissions = db.get_user_permissions(user_id)

# Get users by role
receive_users = db.get_users_by_role('receive_section')
```

### Notesheet Operations
```python
# Create notesheet
notesheet_id = db.create_notesheet(
    notesheet_number='NS/2025/001',
    subject='Annual Budget Approval',
    sender_name='Finance Department',
    received_date='2025-01-09',
    received_by=user_id,
    priority='High',
    category='Financial'
)

# Forward notesheet
db.forward_notesheet(
    notesheet_id=notesheet_id,
    from_user=2,
    to_user=3,
    forwarded_by=2,
    action_taken='Forwarded',
    comments='Please review and approve'
)
```

### Bill Operations
```python
# Create bill
bill_id = db.create_bill(
    bill_number='BILL/2025/001',
    vendor_name='ABC Suppliers',
    bill_date='2025-01-05',
    received_date='2025-01-09',
    received_by=user_id,
    bill_amount=50000.00,
    invoice_number='INV-001',
    vendor_gstin='29ABCDE1234F1Z5',
    gst_amount=9000.00,
    net_payable_amount=59000.00,
    bill_type='Purchase',
    priority='Normal'
)

# Forward bill
db.forward_bill(
    bill_id=bill_id,
    from_user=2,
    to_user=4,
    forwarded_by=2,
    action_taken='Forwarded',
    comments='For verification'
)
```

### Activity Logging
```python
db.log_activity(
    user_id=1,
    activity_type='Forward',
    entity_type='Notesheet',
    entity_id=notesheet_id,
    description='Forwarded notesheet to department head',
    ip_address='192.168.1.100'
)
```

## Security Considerations

### Current Implementation
- Password hashing using SHA-256 (basic)
- Role-based access control
- Activity logging for audit trail

### Production Recommendations
1. **Replace SHA-256 with bcrypt** for password hashing
2. **Implement session management** with secure tokens
3. **Add input validation** for all user inputs
4. **Use prepared statements** (already implemented)
5. **Enable SQLite encryption** for sensitive data
6. **Implement rate limiting** for login attempts
7. **Add two-factor authentication** for sensitive roles
8. **Regular database backups**
9. **SSL/TLS** for database connections in client-server setup

## Common Queries

### Get all notesheets with current holder
```sql
SELECT * FROM vw_current_notesheets;
```

### Get pending items for a user
```sql
SELECT * FROM notesheets 
WHERE current_holder = ? AND current_status != 'Closed';
```

### Get movement history for a notesheet
```sql
SELECT nm.*, 
       u1.full_name as from_user_name,
       u2.full_name as to_user_name
FROM notesheet_movements nm
LEFT JOIN users u1 ON nm.from_user = u1.user_id
LEFT JOIN users u2 ON nm.to_user = u2.user_id
WHERE nm.notesheet_id = ?
ORDER BY nm.forwarded_date DESC;
```

### Get all receive section users
```sql
SELECT * FROM vw_receive_section_users;
```

## Workflow Example

### Receive and Forward a Notesheet
1. Receive section user logs in
2. Creates new notesheet entry (auto-assigned to themselves)
3. Reviews notesheet
4. Forwards to appropriate department head
5. Department head receives notification
6. Department head reviews and either:
   - Approves and forwards to next level
   - Returns with comments
   - Closes the notesheet

### Process a Bill
1. Receive section user receives bill
2. Creates bill entry with vendor and amount details
3. Forwards to accounts officer for verification
4. Accounts officer verifies details
5. Forwards to department head for approval
6. Upon approval, forwards to accounts for payment
7. Payment processed and bill marked as paid

## Maintenance

### Database Backup
```bash
# Backup
sqlite3 wbsedcl_tracking.db ".backup wbsedcl_backup_$(date +%Y%m%d).db"

# Restore
sqlite3 wbsedcl_tracking.db ".restore wbsedcl_backup_20250109.db"
```

### Archive Old Records
```sql
-- Archive notesheets older than 1 year
UPDATE notesheets 
SET is_archived = 1 
WHERE received_date < date('now', '-1 year') 
  AND current_status = 'Closed';
```

### Clean Activity Logs
```sql
-- Delete logs older than 6 months
DELETE FROM activity_logs 
WHERE created_at < datetime('now', '-6 months');
```

## Next Steps
1. Build web application frontend (Flask/Django/FastAPI)
2. Implement file upload functionality
3. Add email notifications
4. Create reports and analytics dashboard
5. Implement barcode/QR code scanning for quick receipt
6. Mobile application for on-the-go access

## Support
For issues or questions, contact the system administrator.

---
**WBSEDCL Internal Tracking System**  
Version 1.0 - January 2025
