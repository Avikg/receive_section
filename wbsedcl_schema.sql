-- WBSEDCL Internal Tracking System Database Schema
-- SQLite3 Database for Notesheet and Bills Management

-- ============================================
-- 1. USER MANAGEMENT TABLES
-- ============================================

-- User Roles Table
CREATE TABLE user_roles (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    role_description TEXT,
    can_receive BOOLEAN DEFAULT 0,
    can_forward BOOLEAN DEFAULT 0,
    can_approve BOOLEAN DEFAULT 0,
    can_manage_users BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users Table
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(15),
    department VARCHAR(100),
    designation VARCHAR(100),
    is_active BOOLEAN DEFAULT 1,
    is_superuser BOOLEAN DEFAULT 0,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- User Role Mapping (Many-to-Many relationship)
CREATE TABLE user_role_mapping (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    assigned_by INTEGER,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES user_roles(role_id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(user_id),
    UNIQUE(user_id, role_id)
);

-- ============================================
-- 2. NOTESHEET MANAGEMENT TABLES
-- ============================================

-- Notesheet Master Table
CREATE TABLE notesheets (
    notesheet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    notesheet_number VARCHAR(50) UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    reference_number VARCHAR(100),
    sender_name VARCHAR(200),
    sender_organization VARCHAR(200),
    sender_address TEXT,
    received_date DATE NOT NULL,
    received_by INTEGER NOT NULL,
    priority VARCHAR(20) DEFAULT 'Normal', -- Low, Normal, High, Urgent
    category VARCHAR(50),
    current_status VARCHAR(50) DEFAULT 'Received', -- Received, In-Progress, Forwarded, Closed, Archived
    current_holder INTEGER,
    remarks TEXT,
    is_archived BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (received_by) REFERENCES users(user_id),
    FOREIGN KEY (current_holder) REFERENCES users(user_id)
);

-- Notesheet Movement/Tracking Table
CREATE TABLE notesheet_movements (
    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    notesheet_id INTEGER NOT NULL,
    from_user INTEGER,
    to_user INTEGER NOT NULL,
    forwarded_by INTEGER NOT NULL,
    forwarded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_taken VARCHAR(50), -- Forwarded, Returned, Approved, Rejected
    comments TEXT,
    expected_return_date DATE,
    is_current BOOLEAN DEFAULT 1,
    FOREIGN KEY (notesheet_id) REFERENCES notesheets(notesheet_id) ON DELETE CASCADE,
    FOREIGN KEY (from_user) REFERENCES users(user_id),
    FOREIGN KEY (to_user) REFERENCES users(user_id),
    FOREIGN KEY (forwarded_by) REFERENCES users(user_id)
);

-- Notesheet Attachments
CREATE TABLE notesheet_attachments (
    attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    notesheet_id INTEGER NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    uploaded_by INTEGER NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    FOREIGN KEY (notesheet_id) REFERENCES notesheets(notesheet_id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
);

-- ============================================
-- 3. BILLS MANAGEMENT TABLES
-- ============================================

-- Bills Master Table
CREATE TABLE bills (
    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_number VARCHAR(50) UNIQUE NOT NULL,
    invoice_number VARCHAR(50),
    vendor_name VARCHAR(200) NOT NULL,
    vendor_address TEXT,
    vendor_gstin VARCHAR(15),
    vendor_pan VARCHAR(10),
    bill_date DATE NOT NULL,
    received_date DATE NOT NULL,
    received_by INTEGER NOT NULL,
    bill_amount DECIMAL(15,2) NOT NULL,
    taxable_amount DECIMAL(15,2),
    gst_amount DECIMAL(15,2),
    tds_amount DECIMAL(15,2),
    net_payable_amount DECIMAL(15,2),
    bill_type VARCHAR(50), -- Purchase, Service, Maintenance, etc.
    category VARCHAR(50),
    description TEXT,
    priority VARCHAR(20) DEFAULT 'Normal',
    current_status VARCHAR(50) DEFAULT 'Received', -- Received, Under Verification, Approved, Payment Pending, Paid, Rejected
    current_holder INTEGER,
    payment_status VARCHAR(50) DEFAULT 'Pending', -- Pending, Processed, Paid, Cancelled
    payment_date DATE,
    payment_reference VARCHAR(100),
    is_archived BOOLEAN DEFAULT 0,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (received_by) REFERENCES users(user_id),
    FOREIGN KEY (current_holder) REFERENCES users(user_id)
);

-- Bill Movement/Tracking Table
CREATE TABLE bill_movements (
    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    from_user INTEGER,
    to_user INTEGER NOT NULL,
    forwarded_by INTEGER NOT NULL,
    forwarded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_taken VARCHAR(50), -- Forwarded, Verified, Approved, Rejected, Returned
    comments TEXT,
    expected_return_date DATE,
    is_current BOOLEAN DEFAULT 1,
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE,
    FOREIGN KEY (from_user) REFERENCES users(user_id),
    FOREIGN KEY (to_user) REFERENCES users(user_id),
    FOREIGN KEY (forwarded_by) REFERENCES users(user_id)
);

-- Bill Attachments
CREATE TABLE bill_attachments (
    attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    uploaded_by INTEGER NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
);

-- ============================================
-- 4. AUDIT AND LOGS TABLES
-- ============================================

-- Activity Logs
CREATE TABLE activity_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    activity_type VARCHAR(50), -- Login, Logout, Create, Update, Delete, Forward
    entity_type VARCHAR(50), -- Notesheet, Bill, User
    entity_id INTEGER,
    description TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================
-- 5. INDEXES FOR PERFORMANCE
-- ============================================

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_user_role_mapping_user ON user_role_mapping(user_id);
CREATE INDEX idx_user_role_mapping_role ON user_role_mapping(role_id);

CREATE INDEX idx_notesheets_number ON notesheets(notesheet_number);
CREATE INDEX idx_notesheets_status ON notesheets(current_status);
CREATE INDEX idx_notesheets_holder ON notesheets(current_holder);
CREATE INDEX idx_notesheets_received_date ON notesheets(received_date);

CREATE INDEX idx_notesheet_movements_notesheet ON notesheet_movements(notesheet_id);
CREATE INDEX idx_notesheet_movements_to_user ON notesheet_movements(to_user);
CREATE INDEX idx_notesheet_movements_current ON notesheet_movements(is_current);

CREATE INDEX idx_bills_number ON bills(bill_number);
CREATE INDEX idx_bills_status ON bills(current_status);
CREATE INDEX idx_bills_holder ON bills(current_holder);
CREATE INDEX idx_bills_received_date ON bills(received_date);
CREATE INDEX idx_bills_vendor ON bills(vendor_name);

CREATE INDEX idx_bill_movements_bill ON bill_movements(bill_id);
CREATE INDEX idx_bill_movements_to_user ON bill_movements(to_user);
CREATE INDEX idx_bill_movements_current ON bill_movements(is_current);

CREATE INDEX idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_type ON activity_logs(activity_type);

-- ============================================
-- 6. INITIAL DATA SETUP
-- ============================================

-- Insert Default Roles
INSERT INTO user_roles (role_name, role_description, can_receive, can_forward, can_approve, can_manage_users) VALUES
('superuser', 'System Administrator with full access', 1, 1, 1, 1),
('receive_section', 'Receive section staff who can receive and forward documents', 1, 1, 0, 0),
('department_head', 'Department head who can approve and forward', 0, 1, 1, 0),
('clerk', 'General clerk with limited access', 0, 1, 0, 0),
('accounts_officer', 'Accounts officer for bill processing', 0, 1, 1, 0),
('viewer', 'Read-only access for viewing documents', 0, 0, 0, 0);

-- Insert Default Superuser (password: admin123 - should be hashed in production)
-- Note: In production, use proper password hashing like bcrypt
INSERT INTO users (username, password_hash, full_name, email, is_active, is_superuser) VALUES
('admin', 'admin123', 'System Administrator', 'admin@wbsedcl.in', 1, 1);

-- Assign superuser role to admin
INSERT INTO user_role_mapping (user_id, role_id, assigned_by) VALUES
(1, 1, 1);

-- ============================================
-- 7. VIEWS FOR COMMON QUERIES
-- ============================================

-- View for Current Notesheet Status
CREATE VIEW vw_current_notesheets AS
SELECT 
    n.notesheet_id,
    n.notesheet_number,
    n.subject,
    n.received_date,
    n.priority,
    n.current_status,
    u1.full_name AS received_by_name,
    u2.full_name AS current_holder_name,
    n.created_at
FROM notesheets n
LEFT JOIN users u1 ON n.received_by = u1.user_id
LEFT JOIN users u2 ON n.current_holder = u2.user_id
WHERE n.is_archived = 0;

-- View for Current Bills Status
CREATE VIEW vw_current_bills AS
SELECT 
    b.bill_id,
    b.bill_number,
    b.vendor_name,
    b.bill_amount,
    b.net_payable_amount,
    b.received_date,
    b.priority,
    b.current_status,
    b.payment_status,
    u1.full_name AS received_by_name,
    u2.full_name AS current_holder_name,
    b.created_at
FROM bills b
LEFT JOIN users u1 ON b.received_by = u1.user_id
LEFT JOIN users u2 ON b.current_holder = u2.user_id
WHERE b.is_archived = 0;

-- View for Users with Receive Section Role
CREATE VIEW vw_receive_section_users AS
SELECT 
    u.user_id,
    u.username,
    u.full_name,
    u.email,
    u.department,
    u.designation,
    u.is_active
FROM users u
INNER JOIN user_role_mapping urm ON u.user_id = urm.user_id
INNER JOIN user_roles ur ON urm.role_id = ur.role_id
WHERE ur.role_name = 'receive_section' 
  AND urm.is_active = 1 
  AND u.is_active = 1;

-- View for User Permissions
CREATE VIEW vw_user_permissions AS
SELECT 
    u.user_id,
    u.username,
    u.full_name,
    GROUP_CONCAT(ur.role_name) AS roles,
    MAX(ur.can_receive) AS can_receive,
    MAX(ur.can_forward) AS can_forward,
    MAX(ur.can_approve) AS can_approve,
    MAX(ur.can_manage_users) AS can_manage_users,
    u.is_superuser
FROM users u
LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id AND urm.is_active = 1
LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
WHERE u.is_active = 1
GROUP BY u.user_id, u.username, u.full_name, u.is_superuser;

-- ============================================
-- 8. TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================

-- Trigger to update notesheet updated_at timestamp
CREATE TRIGGER trg_notesheets_update 
AFTER UPDATE ON notesheets
BEGIN
    UPDATE notesheets SET updated_at = CURRENT_TIMESTAMP WHERE notesheet_id = NEW.notesheet_id;
END;

-- Trigger to update bills updated_at timestamp
CREATE TRIGGER trg_bills_update 
AFTER UPDATE ON bills
BEGIN
    UPDATE bills SET updated_at = CURRENT_TIMESTAMP WHERE bill_id = NEW.bill_id;
END;

-- Trigger to update user updated_at timestamp
CREATE TRIGGER trg_users_update 
AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
END;

-- Trigger to set previous movements as not current when new movement is added
CREATE TRIGGER trg_notesheet_movement_insert
AFTER INSERT ON notesheet_movements
BEGIN
    UPDATE notesheet_movements 
    SET is_current = 0 
    WHERE notesheet_id = NEW.notesheet_id 
      AND movement_id != NEW.movement_id;
    
    UPDATE notesheets 
    SET current_holder = NEW.to_user,
        updated_at = CURRENT_TIMESTAMP
    WHERE notesheet_id = NEW.notesheet_id;
END;

-- Trigger for bill movements
CREATE TRIGGER trg_bill_movement_insert
AFTER INSERT ON bill_movements
BEGIN
    UPDATE bill_movements 
    SET is_current = 0 
    WHERE bill_id = NEW.bill_id 
      AND movement_id != NEW.movement_id;
    
    UPDATE bills 
    SET current_holder = NEW.to_user,
        updated_at = CURRENT_TIMESTAMP
    WHERE bill_id = NEW.bill_id;
END;
