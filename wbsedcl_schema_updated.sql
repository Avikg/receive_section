-- WBSEDCL Tracking System - Complete Schema with Park/Return Support
-- This version includes section hierarchy AND park/return functionality

PRAGMA foreign_keys = ON;

-- ============================================================================
-- SECTIONS AND SUB-SECTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS sections (
    section_id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_name TEXT NOT NULL UNIQUE,
    section_code TEXT UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default sections
INSERT OR IGNORE INTO sections (section_id, section_name, section_code, description) VALUES
(1, 'Receive Section', 'RCV', 'Central receiving section for all documents'),
(2, 'Divisional Manager', 'DM', 'Divisional Manager office'),
(3, 'HR Section', 'HR', 'Human Resources section'),
(4, 'DCC Section', 'DCC', 'Distribution Control Center'),
(5, 'Accounts Section', 'ACC', 'Accounts and Finance section'),
(6, 'Technical 1 Section', 'TECH1', 'Technical section 1'),
(7, 'Technical 2 Section', 'TECH2', 'Technical section 2'),
(8, 'Store Section', 'STORE', 'Stores and inventory section');

CREATE TABLE IF NOT EXISTS sub_sections (
    sub_section_id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER NOT NULL,
    sub_section_name TEXT NOT NULL,
    sub_section_code TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (section_id) REFERENCES sections(section_id),
    UNIQUE(section_id, sub_section_name)
);

-- ============================================================================
-- USER ROLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_roles (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT NOT NULL UNIQUE,
    role_description TEXT,
    can_receive INTEGER DEFAULT 0,
    can_forward INTEGER DEFAULT 0,
    can_approve INTEGER DEFAULT 0,
    can_manage_users INTEGER DEFAULT 0,
    can_edit_any INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert updated roles
INSERT OR IGNORE INTO user_roles (role_id, role_name, role_description, can_receive, can_forward, can_approve, can_manage_users, can_edit_any) VALUES
(1, 'superuser', 'System administrator with full access', 1, 1, 1, 1, 1),
(2, 'receive_section', 'Receive section staff who can receive and forward to any section', 1, 1, 0, 0, 0),
(3, 'section_head', 'Section head who can forward within their section', 0, 1, 1, 0, 0),
(4, 'section_member', 'Section member who can view and work on assigned items', 0, 0, 0, 0, 0),
(5, 'viewer', 'Read-only access to view document status', 0, 0, 0, 0, 0);

-- ============================================================================
-- USERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    section_id INTEGER,
    sub_section_id INTEGER,
    designation TEXT,
    is_section_head INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    is_superuser INTEGER DEFAULT 0,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    FOREIGN KEY (section_id) REFERENCES sections(section_id),
    FOREIGN KEY (sub_section_id) REFERENCES sub_sections(sub_section_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Create default superuser
INSERT OR IGNORE INTO users (user_id, username, password_hash, full_name, email, section_id, designation, is_active, is_superuser) 
VALUES (1, 'admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'System Administrator', 'admin@wbsedcl.in', 1, 'System Administrator', 1, 1);

-- ============================================================================
-- USER ROLE MAPPING
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_role_mapping (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    assigned_by INTEGER,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES user_roles(role_id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(user_id),
    UNIQUE(user_id, role_id)
);

-- Assign superuser role to admin
INSERT OR IGNORE INTO user_role_mapping (user_id, role_id, assigned_by) VALUES (1, 1, 1);

-- ============================================================================
-- NOTESHEETS (WITH PARK/RETURN SUPPORT)
-- ============================================================================

CREATE TABLE IF NOT EXISTS notesheets (
    notesheet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    notesheet_number TEXT NOT NULL UNIQUE,
    subject TEXT NOT NULL,
    sender_name TEXT NOT NULL,
    sender_organization TEXT,
    sender_address TEXT,
    reference_number TEXT,
    received_date DATE NOT NULL,
    category TEXT,
    priority TEXT DEFAULT 'Normal',
    current_status TEXT DEFAULT 'Received',
    current_section_id INTEGER,
    current_sub_section_id INTEGER,
    current_holder INTEGER,
    received_by INTEGER NOT NULL,
    remarks TEXT,
    -- Park/Return fields
    is_parked INTEGER DEFAULT 0,
    park_reason TEXT,
    parked_date TIMESTAMP,
    parked_by INTEGER,
    return_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_section_id) REFERENCES sections(section_id),
    FOREIGN KEY (current_sub_section_id) REFERENCES sub_sections(sub_section_id),
    FOREIGN KEY (current_holder) REFERENCES users(user_id),
    FOREIGN KEY (received_by) REFERENCES users(user_id),
    FOREIGN KEY (parked_by) REFERENCES users(user_id)
);

-- ============================================================================
-- NOTESHEET MOVEMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS notesheet_movements (
    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    notesheet_id INTEGER NOT NULL,
    from_user INTEGER,
    from_section_id INTEGER,
    from_sub_section_id INTEGER,
    to_user INTEGER NOT NULL,
    to_section_id INTEGER,
    to_sub_section_id INTEGER,
    forwarded_by INTEGER NOT NULL,
    forwarded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received_date TIMESTAMP,
    action_taken TEXT,
    comments TEXT,
    is_current INTEGER DEFAULT 1,
    time_held_days INTEGER,
    FOREIGN KEY (notesheet_id) REFERENCES notesheets(notesheet_id) ON DELETE CASCADE,
    FOREIGN KEY (from_user) REFERENCES users(user_id),
    FOREIGN KEY (from_section_id) REFERENCES sections(section_id),
    FOREIGN KEY (from_sub_section_id) REFERENCES sub_sections(sub_section_id),
    FOREIGN KEY (to_user) REFERENCES users(user_id),
    FOREIGN KEY (to_section_id) REFERENCES sections(section_id),
    FOREIGN KEY (to_sub_section_id) REFERENCES sub_sections(sub_section_id),
    FOREIGN KEY (forwarded_by) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS notesheet_attachments (
    attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    notesheet_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    uploaded_by INTEGER NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notesheet_id) REFERENCES notesheets(notesheet_id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
);

-- ============================================================================
-- BILLS (WITH PARK/RETURN SUPPORT)
-- ============================================================================

CREATE TABLE IF NOT EXISTS bills (
    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_number TEXT NOT NULL UNIQUE,
    invoice_number TEXT,
    vendor_name TEXT NOT NULL,
    vendor_address TEXT,
    vendor_gstin TEXT,
    vendor_pan TEXT,
    bill_date DATE,
    received_date DATE NOT NULL,
    bill_amount REAL NOT NULL,
    taxable_amount REAL,
    gst_amount REAL,
    tds_amount REAL,
    net_payable_amount REAL,
    bill_type TEXT,
    category TEXT,
    description TEXT,
    priority TEXT DEFAULT 'Normal',
    current_status TEXT DEFAULT 'Received',
    payment_status TEXT DEFAULT 'Pending',
    current_section_id INTEGER,
    current_sub_section_id INTEGER,
    current_holder INTEGER,
    received_by INTEGER NOT NULL,
    payment_date DATE,
    payment_reference TEXT,
    remarks TEXT,
    -- Park/Return fields
    is_parked INTEGER DEFAULT 0,
    park_reason TEXT,
    parked_date TIMESTAMP,
    parked_by INTEGER,
    return_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_section_id) REFERENCES sections(section_id),
    FOREIGN KEY (current_sub_section_id) REFERENCES sub_sections(sub_section_id),
    FOREIGN KEY (current_holder) REFERENCES users(user_id),
    FOREIGN KEY (received_by) REFERENCES users(user_id),
    FOREIGN KEY (parked_by) REFERENCES users(user_id)
);

-- ============================================================================
-- BILL MOVEMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS bill_movements (
    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    from_user INTEGER,
    from_section_id INTEGER,
    from_sub_section_id INTEGER,
    to_user INTEGER NOT NULL,
    to_section_id INTEGER,
    to_sub_section_id INTEGER,
    forwarded_by INTEGER NOT NULL,
    forwarded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received_date TIMESTAMP,
    action_taken TEXT,
    comments TEXT,
    is_current INTEGER DEFAULT 1,
    time_held_days INTEGER,
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE,
    FOREIGN KEY (from_user) REFERENCES users(user_id),
    FOREIGN KEY (from_section_id) REFERENCES sections(section_id),
    FOREIGN KEY (from_sub_section_id) REFERENCES sub_sections(sub_section_id),
    FOREIGN KEY (to_user) REFERENCES users(user_id),
    FOREIGN KEY (to_section_id) REFERENCES sections(section_id),
    FOREIGN KEY (to_sub_section_id) REFERENCES sub_sections(sub_section_id),
    FOREIGN KEY (forwarded_by) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS bill_attachments (
    attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    uploaded_by INTEGER NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
);

-- ============================================================================
-- ACTIVITY LOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS activity_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activity_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    description TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================================================
-- VIEWS FOR TRACKING AND STATUS
-- ============================================================================

-- View: Current notesheet status with time tracking
CREATE VIEW IF NOT EXISTS vw_notesheet_status AS
SELECT 
    n.notesheet_id,
    n.notesheet_number,
    n.subject,
    n.current_status,
    n.priority,
    n.is_parked,
    s.section_name as current_section,
    ss.sub_section_name as current_sub_section,
    u.full_name as current_holder_name,
    u.designation as current_holder_designation,
    nm.forwarded_date as current_since,
    CAST((julianday('now') - julianday(nm.forwarded_date)) AS INTEGER) as days_held,
    CAST((julianday('now') - julianday(nm.forwarded_date)) * 24 AS INTEGER) as hours_held,
    n.received_date
FROM notesheets n
LEFT JOIN sections s ON n.current_section_id = s.section_id
LEFT JOIN sub_sections ss ON n.current_sub_section_id = ss.sub_section_id
LEFT JOIN users u ON n.current_holder = u.user_id
LEFT JOIN notesheet_movements nm ON n.notesheet_id = nm.notesheet_id AND nm.is_current = 1;

-- View: Current bill status with time tracking
CREATE VIEW IF NOT EXISTS vw_bill_status AS
SELECT 
    b.bill_id,
    b.bill_number,
    b.vendor_name,
    b.bill_amount,
    b.current_status,
    b.payment_status,
    b.priority,
    b.is_parked,
    s.section_name as current_section,
    ss.sub_section_name as current_sub_section,
    u.full_name as current_holder_name,
    u.designation as current_holder_designation,
    bm.forwarded_date as current_since,
    CAST((julianday('now') - julianday(bm.forwarded_date)) AS INTEGER) as days_held,
    CAST((julianday('now') - julianday(bm.forwarded_date)) * 24 AS INTEGER) as hours_held,
    b.received_date
FROM bills b
LEFT JOIN sections s ON b.current_section_id = s.section_id
LEFT JOIN sub_sections ss ON b.current_sub_section_id = ss.sub_section_id
LEFT JOIN users u ON b.current_holder = u.user_id
LEFT JOIN bill_movements bm ON b.bill_id = bm.bill_id AND bm.is_current = 1;

-- View: User permissions
CREATE VIEW IF NOT EXISTS vw_user_permissions AS
SELECT 
    u.user_id,
    u.username,
    u.full_name,
    u.section_id,
    s.section_name,
    u.sub_section_id,
    ss.sub_section_name,
    u.is_section_head,
    u.is_superuser,
    MAX(ur.can_receive) as can_receive,
    MAX(ur.can_forward) as can_forward,
    MAX(ur.can_approve) as can_approve,
    MAX(ur.can_manage_users) as can_manage_users,
    MAX(ur.can_edit_any) as can_edit_any,
    GROUP_CONCAT(ur.role_name) as roles
FROM users u
LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
LEFT JOIN sections s ON u.section_id = s.section_id
LEFT JOIN sub_sections ss ON u.sub_section_id = ss.sub_section_id
GROUP BY u.user_id;

-- View: Section-wise pending items
CREATE VIEW IF NOT EXISTS vw_section_pending AS
SELECT 
    s.section_id,
    s.section_name,
    COUNT(DISTINCT n.notesheet_id) as pending_notesheets,
    COUNT(DISTINCT b.bill_id) as pending_bills,
    COUNT(DISTINCT n.notesheet_id) + COUNT(DISTINCT b.bill_id) as total_pending
FROM sections s
LEFT JOIN notesheets n ON s.section_id = n.current_section_id AND n.current_status != 'Closed'
LEFT JOIN bills b ON s.section_id = b.current_section_id AND b.payment_status = 'Pending'
GROUP BY s.section_id;

-- ============================================================================
-- TRIGGERS FOR AUTO-UPDATES
-- ============================================================================

-- Update notesheet timestamp on update
CREATE TRIGGER IF NOT EXISTS update_notesheet_timestamp 
AFTER UPDATE ON notesheets
BEGIN
    UPDATE notesheets SET updated_at = CURRENT_TIMESTAMP WHERE notesheet_id = NEW.notesheet_id;
END;

-- Update bill timestamp on update
CREATE TRIGGER IF NOT EXISTS update_bill_timestamp 
AFTER UPDATE ON bills
BEGIN
    UPDATE bills SET updated_at = CURRENT_TIMESTAMP WHERE bill_id = NEW.bill_id;
END;

-- Mark previous movement as not current when new movement is added
CREATE TRIGGER IF NOT EXISTS mark_previous_notesheet_movement
AFTER INSERT ON notesheet_movements
BEGIN
    UPDATE notesheet_movements 
    SET is_current = 0 
    WHERE notesheet_id = NEW.notesheet_id 
    AND movement_id != NEW.movement_id;
    
    UPDATE notesheets
    SET current_holder = NEW.to_user,
        current_section_id = NEW.to_section_id,
        current_sub_section_id = NEW.to_sub_section_id
    WHERE notesheet_id = NEW.notesheet_id;
END;

-- Mark previous bill movement as not current when new movement is added
CREATE TRIGGER IF NOT EXISTS mark_previous_bill_movement
AFTER INSERT ON bill_movements
BEGIN
    UPDATE bill_movements 
    SET is_current = 0 
    WHERE bill_id = NEW.bill_id 
    AND movement_id != NEW.movement_id;
    
    UPDATE bills
    SET current_holder = NEW.to_user,
        current_section_id = NEW.to_section_id,
        current_sub_section_id = NEW.to_sub_section_id
    WHERE bill_id = NEW.bill_id;
END;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_notesheets_number ON notesheets(notesheet_number);
CREATE INDEX IF NOT EXISTS idx_notesheets_status ON notesheets(current_status);
CREATE INDEX IF NOT EXISTS idx_notesheets_holder ON notesheets(current_holder);
CREATE INDEX IF NOT EXISTS idx_notesheets_section ON notesheets(current_section_id);
CREATE INDEX IF NOT EXISTS idx_notesheets_parked ON notesheets(is_parked);
CREATE INDEX IF NOT EXISTS idx_notesheet_movements_notesheet ON notesheet_movements(notesheet_id);
CREATE INDEX IF NOT EXISTS idx_notesheet_movements_current ON notesheet_movements(is_current);

CREATE INDEX IF NOT EXISTS idx_bills_number ON bills(bill_number);
CREATE INDEX IF NOT EXISTS idx_bills_status ON bills(current_status);
CREATE INDEX IF NOT EXISTS idx_bills_holder ON bills(current_holder);
CREATE INDEX IF NOT EXISTS idx_bills_section ON bills(current_section_id);
CREATE INDEX IF NOT EXISTS idx_bills_parked ON bills(is_parked);
CREATE INDEX IF NOT EXISTS idx_bill_movements_bill ON bill_movements(bill_id);
CREATE INDEX IF NOT EXISTS idx_bill_movements_current ON bill_movements(is_current);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_section ON users(section_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_date ON activity_logs(created_at);