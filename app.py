"""
WBSEDCL Tracking System - Main Application with Section Support
Flask web application for notesheet and bill tracking
"""

"""
WBSEDCL Document Tracking System
VERSION: 2026-01-11-FIXED-FORWARDING-v4
Last Updated: 2026-01-11
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from init_database import WBSEDCLDatabase
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'wbsedcl-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, username, full_name, email, section_id, is_active, is_superuser):
        self.id = user_id
        self.username = username
        self.full_name = full_name
        self.email = email
        self.section_id = section_id
        self._is_active = bool(is_active)
        self.is_superuser = bool(is_superuser)
        self._permissions = None

    @property
    def is_active(self):
        return self._is_active
    
    def get_permissions(self):
        """Get user permissions from database"""
        if self._permissions is None:
            db = WBSEDCLDatabase()
            self._permissions = db.get_user_permissions(self.id)
            db.close()
        return self._permissions
    
    def can_receive(self):
        """Check if user can receive documents"""
        return self.is_superuser or self.get_permissions().get('can_receive', False)
    
    def can_forward(self):
        """Check if user can forward documents"""
        return self.is_superuser or self.get_permissions().get('can_forward', False)
    
    def can_approve(self):
        """Check if user can approve documents"""
        return self.is_superuser or self.get_permissions().get('can_approve', False)
    
    def can_manage_users(self):
        """Check if user can manage users"""
        return self.is_superuser
    
    def is_receive_section(self):
        """Check if user is in Receive Section"""
        return self.section_id == 1 or self.is_superuser
    
    def is_section_head(self):
        """Check if user is a section head"""
        if self.is_superuser:
            return True
        
        # Query database directly to check if user has section_head role
        db = WBSEDCLDatabase()
        conn = db.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM user_role_mapping urm
            JOIN user_roles ur ON urm.role_id = ur.role_id
            WHERE urm.user_id = ? AND ur.role_name = 'section_head'
        ''', (self.id,))
        
        has_role = cursor.fetchone()[0] > 0
        db.close()
        
        return has_role

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, full_name, email, section_id, is_active, is_superuser
        FROM users WHERE user_id = ?
    ''', (user_id,))
    user_data = cursor.fetchone()
    db.close()
    
    if user_data and user_data[5]:  # Check is_active
        return User(*user_data)
    return None

# Permission decorators
def receive_permission_required(f):
    """Decorator to require receive permission"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_receive():
            flash('You do not have permission to receive documents.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def forward_permission_required(f):
    """Decorator to require forward permission"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_forward():
            flash('You do not have permission to forward documents.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin/superuser permission"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_manage_users():
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes

@app.route('/')
def index():
    """Redirect to dashboard or login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/version')
def version_check():
    """Quick version check"""
    return "VERSION: 2026-01-12-WITH-SEARCH-REPORTS"

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        db = WBSEDCLDatabase()
        user_data = db.authenticate_user(username, password)
        
        if user_data:
            # Generate unique session ID
            import uuid
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            
            # Update last login
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_login = ? WHERE user_id = ?', 
                         (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_data['user_id']))
            conn.commit()
            
            # Log activity with session ID
            db.log_activity(user_data['user_id'], 'login', 'User logged in', request.remote_addr, session_id)
            db.close()
            
            # Create user object and login
            user = User(
                user_data['user_id'],
                user_data['username'],
                user_data['full_name'],
                user_data['email'],
                user_data.get('section_id'),
                user_data['is_active'],
                user_data['is_superuser']
            )
            login_user(user, remember=remember)
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Failed login - check if username exists
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE username = ?', (username,))
            user_exists = cursor.fetchone()
            
            if user_exists:
                # User exists but wrong password
                db.log_activity(
                    user_exists[0], 
                    'login_failed', 
                    f'Failed login: Invalid password. Username attempted: {username}', 
                    request.remote_addr,
                    None  # No session for failed login
                )
            else:
                # Username doesn't exist - use system user_id = 0
                db.log_activity(
                    0,
                    'login_failed',
                    f'Failed login: Invalid username and password. Username attempted: {username}',
                    request.remote_addr,
                    None  # No session for failed login
                )
            
            db.close()
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    db = WBSEDCLDatabase()
    session_id = session.get('session_id', None)
    db.log_activity(current_user.id, 'logout', 'User logged out', request.remote_addr, session_id)
    db.close()
    
    # Clear session
    session.pop('session_id', None)
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    """User profile page"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Get form data
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        designation = request.form.get('designation')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Superuser can change username and section
        username = request.form.get('username') if current_user.is_superuser else None
        section_id = request.form.get('section_id') if current_user.is_superuser else None
        
        # Validate
        if not full_name:
            flash('Full name is required.', 'error')
            db.close()
            return redirect(url_for('user_profile'))
        
        # Password change validation
        if new_password:
            if not current_password:
                flash('Current password is required to set a new password.', 'error')
                db.close()
                return redirect(url_for('user_profile'))
            
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                db.close()
                return redirect(url_for('user_profile'))
            
            # Verify current password
            import hashlib
            current_hash = hashlib.sha256(current_password.encode()).hexdigest()
            cursor.execute('SELECT password_hash FROM users WHERE user_id = ?', (current_user.id,))
            stored_hash = cursor.fetchone()[0]
            
            if current_hash != stored_hash:
                flash('Current password is incorrect.', 'error')
                db.close()
                return redirect(url_for('user_profile'))
            
            # Update with new password
            new_hash = hashlib.sha256(new_password.encode()).hexdigest()
            
            if current_user.is_superuser and username and section_id:
                cursor.execute('''
                    UPDATE users SET 
                        username = ?, full_name = ?, email = ?, phone = ?, 
                        designation = ?, section_id = ?, password_hash = ?
                    WHERE user_id = ?
                ''', (username, full_name, email, phone, designation, section_id, new_hash, current_user.id))
            else:
                cursor.execute('''
                    UPDATE users SET 
                        full_name = ?, email = ?, phone = ?, designation = ?, password_hash = ?
                    WHERE user_id = ?
                ''', (full_name, email, phone, designation, new_hash, current_user.id))
            
            flash('Profile and password updated successfully!', 'success')
        else:
            # Update without password change
            if current_user.is_superuser and username and section_id:
                cursor.execute('''
                    UPDATE users SET 
                        username = ?, full_name = ?, email = ?, phone = ?, 
                        designation = ?, section_id = ?
                    WHERE user_id = ?
                ''', (username, full_name, email, phone, designation, section_id, current_user.id))
            else:
                cursor.execute('''
                    UPDATE users SET 
                        full_name = ?, email = ?, phone = ?, designation = ?
                    WHERE user_id = ?
                ''', (full_name, email, phone, designation, current_user.id))
            
            flash('Profile updated successfully!', 'success')
        
        conn.commit()
        
        # Log activity
        session_id = session.get('session_id', None)
        db.log_activity(
            current_user.id,
            'profile_updated',
            'User updated their profile',
            request.remote_addr,
            session_id
        )
        
        db.close()
        return redirect(url_for('user_profile'))
    
    # GET - Load user data
    cursor.execute('''
        SELECT 
            u.user_id, u.username, u.full_name, u.email, u.phone,
            u.section_id, s.section_name, u.designation, 
            u.is_active, u.is_superuser, u.last_login,
            GROUP_CONCAT(ur.role_name) as roles
        FROM users u
        LEFT JOIN sections s ON u.section_id = s.section_id
        LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
        LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
        WHERE u.user_id = ?
        GROUP BY u.user_id
    ''', (current_user.id,))
    
    user_data = cursor.fetchone()
    columns = [desc[0] for desc in cursor.description]
    user = dict(zip(columns, user_data))
    
    # Get all sections (for superuser)
    sections = []
    if current_user.is_superuser:
        sections = db.get_all_sections()
    
    db.close()
    
    return render_template('user_profile.html', user=user, sections=sections)

# =============================================================================
# UPDATED DASHBOARD ROUTE - Replace existing dashboard route in app.py
# This includes Letters statistics
# =============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get statistics for CURRENT USER ONLY
    
    # My Notesheets - where I'm the current holder
    cursor.execute('SELECT COUNT(*) FROM notesheets WHERE current_holder = ?', (current_user.id,))
    my_notesheets = cursor.fetchone()[0]
    
    # My Pending Notesheets - where I'm the current holder and status is not Closed
    cursor.execute("SELECT COUNT(*) FROM notesheets WHERE current_holder = ? AND current_status != 'Closed'", 
                   (current_user.id,))
    my_pending_notesheets = cursor.fetchone()[0]
    
    # My Bills - where I'm the current holder
    cursor.execute('SELECT COUNT(*) FROM bills WHERE current_holder = ?', (current_user.id,))
    my_bills = cursor.fetchone()[0]
    
    # My Pending Bills - where I'm the current holder and payment status is Pending
    cursor.execute("SELECT COUNT(*) FROM bills WHERE current_holder = ? AND payment_status = 'Pending'", 
                   (current_user.id,))
    my_pending_bills = cursor.fetchone()[0]
    
    # My Letters - where I'm the current holder
    cursor.execute('SELECT COUNT(*) FROM letters WHERE current_holder = ?', (current_user.id,))
    my_letters = cursor.fetchone()[0]
    
    # My Pending Letters - where I'm the current holder and status is not Closed/Replied
    cursor.execute("""
        SELECT COUNT(*) FROM letters 
        WHERE current_holder = ? 
        AND current_status NOT IN ('Closed', 'Replied', 'Archived')
    """, (current_user.id,))
    my_pending_letters = cursor.fetchone()[0]
    
    # Total items with me (for "My Pending Items" card)
    my_pending_items = my_pending_notesheets + my_pending_bills + my_pending_letters
    
    # Get parked documents count (Receive Section only)
    parked_count = 0
    if current_user.is_receive_section():
        cursor.execute('SELECT COUNT(*) FROM notesheets WHERE is_parked = 1')
        parked_ns = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM bills WHERE is_parked = 1')
        parked_bills = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM letters WHERE is_parked = 1')
        parked_letters = cursor.fetchone()[0]
        parked_count = parked_ns + parked_bills + parked_letters
    
    # Get recent notesheets (last 5)
    cursor.execute('''
        SELECT notesheet_id, notesheet_number, subject, received_date, current_status
        FROM notesheets
        WHERE current_holder = ?
        ORDER BY received_date DESC
        LIMIT 5
    ''', (current_user.id,))
    recent_notesheets = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    recent_notesheets = [dict(zip(columns, row)) for row in recent_notesheets]
    
    # Get recent bills (last 5)
    cursor.execute('''
        SELECT bill_id, bill_number, vendor_name, bill_amount, payment_status
        FROM bills
        WHERE current_holder = ?
        ORDER BY received_date DESC
        LIMIT 5
    ''', (current_user.id,))
    recent_bills = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    recent_bills = [dict(zip(columns, row)) for row in recent_bills]
    
    # Get recent letters (last 5)
    cursor.execute('''
        SELECT letter_id, letter_number, subject, received_date, current_status, reply_required
        FROM letters
        WHERE current_holder = ?
        ORDER BY received_date DESC
        LIMIT 5
    ''', (current_user.id,))
    recent_letters = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    recent_letters = [dict(zip(columns, row)) for row in recent_letters]
    
    db.close()
    
    stats = {
        'total_notesheets': my_notesheets,
        'pending_notesheets': my_pending_notesheets,
        'total_bills': my_bills,
        'pending_bills': my_pending_bills,
        'total_letters': my_letters,
        'pending_letters': my_pending_letters,
        'my_pending_items': my_pending_items,
        'parked_items': parked_count
    }
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_notesheets=recent_notesheets,
                         recent_bills=recent_bills,
                         recent_letters=recent_letters)


@app.route('/my-notesheets')
@login_required
def my_notesheets():
    """Show notesheets assigned to current user"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get notesheets where current user is the holder
    cursor.execute('''
        SELECT 
            n.notesheet_id, n.notesheet_number, n.subject, n.sender_name,
            n.received_date, n.current_status, n.priority, n.is_parked,
            u.full_name as current_holder_name,
            s.section_name as current_section_name
        FROM notesheets n
        LEFT JOIN users u ON n.current_holder = u.user_id
        LEFT JOIN sections s ON n.current_section_id = s.section_id
        WHERE n.current_holder = ?
        ORDER BY n.received_date DESC
    ''', (current_user.id,))
    
    notesheets = cursor.fetchall()
    
    # Convert to list of dicts
    columns = [desc[0] for desc in cursor.description]
    notesheets = [dict(zip(columns, row)) for row in notesheets]
    
    db.close()
    
    return render_template('notesheets/list.html', notesheets=notesheets, filter_type='my')

@app.route('/my-bills')
@login_required
def my_bills():
    """Show bills assigned to current user"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get bills where current user is the holder
    cursor.execute('''
        SELECT 
            b.bill_id, b.bill_number, b.invoice_number, b.vendor_name,
            b.bill_amount, b.received_date, b.current_status, b.payment_status, b.priority,
            u.full_name as current_holder_name,
            s.section_name as current_section_name
        FROM bills b
        LEFT JOIN users u ON b.current_holder = u.user_id
        LEFT JOIN sections s ON b.current_section_id = s.section_id
        WHERE b.current_holder = ?
        ORDER BY b.received_date DESC
    ''', (current_user.id,))
    
    bills = cursor.fetchall()
    
    # Convert to list of dicts
    columns = [desc[0] for desc in cursor.description]
    bills = [dict(zip(columns, row)) for row in bills]
    
    db.close()
    
    return render_template('bills/list.html', bills=bills, filter_type='my')


"""
COMPLETELY CLEAN Advanced Search Route
NO movement_id, NO is_current - just uses main tables
"""

@app.route('/search/advanced', methods=['GET'])
@login_required
def advanced_search():
    """Advanced search with multiple filters - INCLUDING LETTERS"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get filter parameters
    doc_type = request.args.get('doc_type', 'all')
    status = request.args.get('status', 'all')
    priority = request.args.get('priority', 'all')
    section_id = request.args.get('section_id', 'all')
    holder_id = request.args.get('holder_id', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    min_days = request.args.get('min_days', '')
    keywords = request.args.get('keywords', '')
    doc_number = request.args.get('doc_number', '')
    sender = request.args.get('sender', '')
    
    results = []
    
    # Only search if at least one filter is applied
    if any([doc_type != 'all', status != 'all', priority != 'all', 
            section_id != 'all', holder_id != 'all', date_from, date_to, 
            min_days, keywords, doc_number, sender]):
        
        # Search Notesheets
        if doc_type in ['all', 'notesheet']:
            ns_query = '''
                SELECT 
                    'notesheet' as doc_type,
                    n.notesheet_id as doc_id,
                    n.notesheet_number as doc_number,
                    n.subject,
                    n.sender_name,
                    n.priority,
                    n.is_parked,
                    n.current_status as status,
                    u.full_name as holder_name,
                    s.section_name,
                    n.received_date as in_date,
                    CAST(julianday('now') - julianday(n.received_date) AS INTEGER) as days_held
                FROM notesheets n
                LEFT JOIN users u ON n.current_holder = u.user_id
                LEFT JOIN sections s ON n.current_section_id = s.section_id
                WHERE 1=1
            '''
            params = []
            
            if status == 'parked':
                ns_query += ' AND n.is_parked = 1'
            elif status == 'active':
                ns_query += ' AND n.is_parked = 0'
            
            if priority != 'all':
                ns_query += ' AND n.priority = ?'
                params.append(priority)
            
            if section_id != 'all':
                ns_query += ' AND n.current_section_id = ?'
                params.append(section_id)
            
            if holder_id != 'all':
                ns_query += ' AND n.current_holder = ?'
                params.append(holder_id)
            
            if date_from:
                ns_query += ' AND DATE(n.received_date) >= ?'
                params.append(date_from)
            
            if date_to:
                ns_query += ' AND DATE(n.received_date) <= ?'
                params.append(date_to)
            
            if keywords:
                ns_query += ' AND (n.subject LIKE ? OR n.notesheet_number LIKE ? OR n.sender_name LIKE ?)'
                keyword_param = f'%{keywords}%'
                params.extend([keyword_param, keyword_param, keyword_param])
            
            if doc_number:
                ns_query += ' AND n.notesheet_number LIKE ?'
                params.append(f'%{doc_number}%')
            
            if sender:
                ns_query += ' AND n.sender_name LIKE ?'
                params.append(f'%{sender}%')
            
            cursor.execute(ns_query, params)
            ns_results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            results.extend([dict(zip(columns, row)) for row in ns_results])
        
        # Search Bills
        if doc_type in ['all', 'bill']:
            bill_query = '''
                SELECT 
                    'bill' as doc_type,
                    b.bill_id as doc_id,
                    b.bill_number as doc_number,
                    b.vendor_name as subject,
                    b.vendor_name as sender_name,
                    b.priority,
                    b.is_parked,
                    b.payment_status as status,
                    u.full_name as holder_name,
                    s.section_name,
                    b.received_date as in_date,
                    CAST(julianday('now') - julianday(b.received_date) AS INTEGER) as days_held
                FROM bills b
                LEFT JOIN users u ON b.current_holder = u.user_id
                LEFT JOIN sections s ON b.current_section_id = s.section_id
                WHERE 1=1
            '''
            params = []
            
            if status == 'parked':
                bill_query += ' AND b.is_parked = 1'
            elif status == 'active':
                bill_query += ' AND b.is_parked = 0'
            elif status == 'cleared':
                bill_query += ' AND b.payment_status = "Paid"'
            
            if priority != 'all':
                bill_query += ' AND b.priority = ?'
                params.append(priority)
            
            if section_id != 'all':
                bill_query += ' AND b.current_section_id = ?'
                params.append(section_id)
            
            if holder_id != 'all':
                bill_query += ' AND b.current_holder = ?'
                params.append(holder_id)
            
            if date_from:
                bill_query += ' AND DATE(b.received_date) >= ?'
                params.append(date_from)
            
            if date_to:
                bill_query += ' AND DATE(b.received_date) <= ?'
                params.append(date_to)
            
            if keywords:
                bill_query += ' AND (b.vendor_name LIKE ? OR b.bill_number LIKE ? OR b.invoice_number LIKE ?)'
                keyword_param = f'%{keywords}%'
                params.extend([keyword_param, keyword_param, keyword_param])
            
            if doc_number:
                bill_query += ' AND b.bill_number LIKE ?'
                params.append(f'%{doc_number}%')
            
            if sender:
                bill_query += ' AND b.vendor_name LIKE ?'
                params.append(f'%{sender}%')
            
            cursor.execute(bill_query, params)
            bill_results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            results.extend([dict(zip(columns, row)) for row in bill_results])
        
        # Search Letters (NEW!)
        if doc_type in ['all', 'letter']:
            letter_query = '''
                SELECT 
                    'letter' as doc_type,
                    l.letter_id as doc_id,
                    l.letter_number as doc_number,
                    l.subject,
                    l.sender_name,
                    l.priority,
                    l.is_parked,
                    l.current_status as status,
                    u.full_name as holder_name,
                    s.section_name,
                    l.received_date as in_date,
                    CAST(julianday('now') - julianday(l.received_date) AS INTEGER) as days_held
                FROM letters l
                LEFT JOIN users u ON l.current_holder = u.user_id
                LEFT JOIN sections s ON l.current_section_id = s.section_id
                WHERE 1=1
            '''
            params = []
            
            if status == 'parked':
                letter_query += ' AND l.is_parked = 1'
            elif status == 'active':
                letter_query += ' AND l.is_parked = 0'
            elif status == 'closed':
                letter_query += ' AND l.current_status = "Closed"'
            
            if priority != 'all':
                letter_query += ' AND l.priority = ?'
                params.append(priority)
            
            if section_id != 'all':
                letter_query += ' AND l.current_section_id = ?'
                params.append(section_id)
            
            if holder_id != 'all':
                letter_query += ' AND l.current_holder = ?'
                params.append(holder_id)
            
            if date_from:
                letter_query += ' AND DATE(l.received_date) >= ?'
                params.append(date_from)
            
            if date_to:
                letter_query += ' AND DATE(l.received_date) <= ?'
                params.append(date_to)
            
            if keywords:
                letter_query += ' AND (l.subject LIKE ? OR l.letter_number LIKE ? OR l.sender_name LIKE ?)'
                keyword_param = f'%{keywords}%'
                params.extend([keyword_param, keyword_param, keyword_param])
            
            if doc_number:
                letter_query += ' AND l.letter_number LIKE ?'
                params.append(f'%{doc_number}%')
            
            if sender:
                letter_query += ' AND l.sender_name LIKE ?'
                params.append(f'%{sender}%')
            
            cursor.execute(letter_query, params)
            letter_results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            results.extend([dict(zip(columns, row)) for row in letter_results])
        
        # Filter by minimum days held
        if min_days:
            results = [r for r in results if r.get('days_held', 0) >= int(min_days)]
        
        # Sort by days_held descending
        results.sort(key=lambda x: x.get('days_held', 0), reverse=True)
    
    # Get all sections for filter dropdown
    sections = db.get_all_sections()
    
    # Get all users for filter dropdown
    cursor.execute('SELECT user_id, username, full_name FROM users WHERE is_active = 1 ORDER BY full_name')
    users = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    users = [dict(zip(columns, row)) for row in users]
    
    db.close()
    
    return render_template('advanced_search.html',
                         results=results,
                         sections=sections,
                         users=users,
                         filters={
                             'doc_type': doc_type,
                             'status': status,
                             'priority': priority,
                             'section_id': section_id,
                             'holder_id': holder_id,
                             'date_from': date_from,
                             'date_to': date_to,
                             'min_days': min_days,
                             'keywords': keywords,
                             'doc_number': doc_number,
                             'sender': sender
                         })


"""
ULTRA-SIMPLIFIED Advanced Reports Route
Works without current_movement_id - uses current_holder only
"""

@app.route('/reports/advanced', methods=['GET'])
@login_required
def advanced_reports():
    """Generate advanced reports - UPDATED WITH LETTERS"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    report_type = request.args.get('report_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    report_data = None
    aging_summary = None
    
    if report_type:
        # Section Performance Report - UPDATED WITH LETTERS
        if report_type == 'section_performance':
            query = '''
                SELECT 
                    s.section_name,
                    COUNT(DISTINCT n.notesheet_id) + COUNT(DISTINCT b.bill_id) + COUNT(DISTINCT l.letter_id) as total_docs,
                    AVG(julianday('now') - julianday(COALESCE(n.received_date, b.received_date, l.received_date))) as avg_days,
                    SUM(CASE WHEN n.current_holder IS NOT NULL AND n.is_parked = 0 THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN b.current_holder IS NOT NULL AND b.is_parked = 0 THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN l.current_holder IS NOT NULL AND l.is_parked = 0 THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN n.current_status = 'Closed' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN b.payment_status = 'Paid' THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN l.current_status = 'Closed' THEN 1 ELSE 0 END) as cleared
                FROM sections s
                LEFT JOIN notesheets n ON s.section_id = n.current_section_id
                LEFT JOIN bills b ON s.section_id = b.current_section_id
                LEFT JOIN letters l ON s.section_id = l.current_section_id
                WHERE 1=1
            '''
            params = []
            
            if date_from:
                query += ' AND (n.received_date >= ? OR b.received_date >= ? OR l.received_date >= ?)'
                params.extend([date_from, date_from, date_from])
            
            if date_to:
                query += ' AND (n.received_date <= ? OR b.received_date <= ? OR l.received_date <= ?)'
                params.extend([date_to, date_to, date_to])
            
            query += ' GROUP BY s.section_id HAVING total_docs > 0 ORDER BY avg_days DESC'
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            report_data = [dict(zip(columns, row)) for row in results]
        
        # User Productivity Report - UPDATED WITH LETTERS
        elif report_type == 'user_productivity':
            query = '''
                SELECT 
                    u.full_name,
                    s.section_name,
                    COUNT(DISTINCT nm.movement_id) + COUNT(DISTINCT bm.movement_id) + COUNT(DISTINCT lm.movement_id) as processed,
                    AVG(julianday('now') - julianday(COALESCE(nm.forwarded_date, bm.forwarded_date, lm.forwarded_date))) as avg_days,
                    COUNT(DISTINCT n.notesheet_id) + COUNT(DISTINCT b.bill_id) + COUNT(DISTINCT l.letter_id) as holding
                FROM users u
                LEFT JOIN sections s ON u.section_id = s.section_id
                LEFT JOIN notesheet_movements nm ON u.user_id = nm.from_user
                LEFT JOIN bill_movements bm ON u.user_id = bm.from_user
                LEFT JOIN letter_movements lm ON u.user_id = lm.from_user
                LEFT JOIN notesheets n ON u.user_id = n.current_holder
                LEFT JOIN bills b ON u.user_id = b.current_holder
                LEFT JOIN letters l ON u.user_id = l.current_holder
                WHERE u.is_active = 1 AND u.is_superuser = 0
            '''
            params = []
            
            if date_from:
                query += ' AND (nm.forwarded_date >= ? OR bm.forwarded_date >= ? OR lm.forwarded_date >= ?)'
                params.extend([date_from, date_from, date_from])
            
            if date_to:
                query += ' AND (nm.forwarded_date <= ? OR bm.forwarded_date <= ? OR lm.forwarded_date <= ?)'
                params.extend([date_to, date_to, date_to])
            
            query += ' GROUP BY u.user_id HAVING processed > 0 ORDER BY processed DESC LIMIT 20'
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            report_data = [dict(zip(columns, row)) for row in results]
        
        # Document Aging Report - UPDATED WITH LETTERS
        elif report_type == 'document_aging':
            # Get aging summary - using received_date as proxy
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN days_held <= 3 THEN 1 ELSE 0 END) as fresh,
                    SUM(CASE WHEN days_held > 3 AND days_held <= 7 THEN 1 ELSE 0 END) as moderate,
                    SUM(CASE WHEN days_held > 7 AND days_held <= 14 THEN 1 ELSE 0 END) as old,
                    SUM(CASE WHEN days_held > 14 THEN 1 ELSE 0 END) as critical
                FROM (
                    SELECT 
                        CAST(julianday('now') - julianday(received_date) AS INTEGER) as days_held
                    FROM notesheets
                    WHERE is_parked = 0 AND current_holder IS NOT NULL
                    UNION ALL
                    SELECT 
                        CAST(julianday('now') - julianday(received_date) AS INTEGER) as days_held
                    FROM bills
                    WHERE is_parked = 0 AND current_holder IS NOT NULL
                    UNION ALL
                    SELECT 
                        CAST(julianday('now') - julianday(received_date) AS INTEGER) as days_held
                    FROM letters
                    WHERE is_parked = 0 AND current_holder IS NOT NULL
                )
            ''')
            aging_result = cursor.fetchone()
            aging_summary = dict(zip(['fresh', 'moderate', 'old', 'critical'], aging_result)) if aging_result else {'fresh': 0, 'moderate': 0, 'old': 0, 'critical': 0}
            
            # Get detailed aging data
            query = '''
                SELECT 
                    'notesheet' as doc_type,
                    n.notesheet_id as doc_id,
                    n.notesheet_number as doc_number,
                    n.subject,
                    u.full_name as holder_name,
                    n.priority,
                    CAST(julianday('now') - julianday(n.received_date) AS INTEGER) as days_held
                FROM notesheets n
                LEFT JOIN users u ON n.current_holder = u.user_id
                WHERE n.is_parked = 0 AND n.current_holder IS NOT NULL
                UNION ALL
                SELECT 
                    'bill' as doc_type,
                    b.bill_id as doc_id,
                    b.bill_number as doc_number,
                    b.vendor_name as subject,
                    u.full_name as holder_name,
                    b.priority,
                    CAST(julianday('now') - julianday(b.received_date) AS INTEGER) as days_held
                FROM bills b
                LEFT JOIN users u ON b.current_holder = u.user_id
                WHERE b.is_parked = 0 AND b.current_holder IS NOT NULL
                UNION ALL
                SELECT 
                    'letter' as doc_type,
                    l.letter_id as doc_id,
                    l.letter_number as doc_number,
                    l.subject,
                    u.full_name as holder_name,
                    l.priority,
                    CAST(julianday('now') - julianday(l.received_date) AS INTEGER) as days_held
                FROM letters l
                LEFT JOIN users u ON l.current_holder = u.user_id
                WHERE l.is_parked = 0 AND l.current_holder IS NOT NULL
                ORDER BY days_held DESC
                LIMIT 50
            '''
            
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            report_data = [dict(zip(columns, row)) for row in results]
        
        # Bottleneck Analysis Report - UPDATED WITH LETTERS
        elif report_type == 'bottleneck_analysis':
            query = '''
                SELECT 
                    s.section_name,
                    u.full_name as user_name,
                    COUNT(DISTINCT n.notesheet_id) + COUNT(DISTINCT b.bill_id) + COUNT(DISTINCT l.letter_id) as pending_count,
                    AVG(julianday('now') - julianday(COALESCE(n.received_date, b.received_date, l.received_date))) as avg_wait_days,
                    MAX(julianday('now') - julianday(COALESCE(n.received_date, b.received_date, l.received_date))) as max_wait_days
                FROM users u
                JOIN sections s ON u.section_id = s.section_id
                LEFT JOIN notesheets n ON u.user_id = n.current_holder AND n.is_parked = 0
                LEFT JOIN bills b ON u.user_id = b.current_holder AND b.is_parked = 0
                LEFT JOIN letters l ON u.user_id = l.current_holder AND l.is_parked = 0
                WHERE u.is_active = 1
                GROUP BY u.user_id
                HAVING pending_count > 2
                ORDER BY avg_wait_days DESC, pending_count DESC
                LIMIT 20
            '''
            
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            report_data = [dict(zip(columns, row)) for row in results]
        
        # Monthly Summary Report - UPDATED WITH LETTERS
        elif report_type == 'monthly_summary':
            query = '''
                SELECT 
                    month,
                    SUM(notesheets_received) as notesheets_received,
                    SUM(bills_received) as bills_received,
                    SUM(letters_received) as letters_received,
                    SUM(notesheets_cleared) as notesheets_cleared,
                    SUM(bills_paid) as bills_paid,
                    SUM(letters_closed) as letters_closed,
                    AVG(CASE WHEN avg_notesheet_days > 0 THEN avg_notesheet_days END) as avg_notesheet_days,
                    AVG(CASE WHEN avg_bill_days > 0 THEN avg_bill_days END) as avg_bill_days,
                    AVG(CASE WHEN avg_letter_days > 0 THEN avg_letter_days END) as avg_letter_days
                FROM (
                    SELECT 
                        strftime('%Y-%m', received_date) as month,
                        COUNT(*) as notesheets_received,
                        0 as bills_received,
                        0 as letters_received,
                        SUM(CASE WHEN current_status = 'Closed' THEN 1 ELSE 0 END) as notesheets_cleared,
                        0 as bills_paid,
                        0 as letters_closed,
                        AVG(julianday('now') - julianday(received_date)) as avg_notesheet_days,
                        0 as avg_bill_days,
                        0 as avg_letter_days
                    FROM notesheets
                    WHERE strftime('%Y-%m', received_date) >= strftime('%Y-%m', 'now', '-12 months')
                    GROUP BY month
                    UNION ALL
                    SELECT 
                        strftime('%Y-%m', received_date) as month,
                        0 as notesheets_received,
                        COUNT(*) as bills_received,
                        0 as letters_received,
                        0 as notesheets_cleared,
                        SUM(CASE WHEN payment_status = 'Paid' THEN 1 ELSE 0 END) as bills_paid,
                        0 as letters_closed,
                        0 as avg_notesheet_days,
                        AVG(julianday('now') - julianday(received_date)) as avg_bill_days,
                        0 as avg_letter_days
                    FROM bills
                    WHERE strftime('%Y-%m', received_date) >= strftime('%Y-%m', 'now', '-12 months')
                    GROUP BY month
                    UNION ALL
                    SELECT 
                        strftime('%Y-%m', received_date) as month,
                        0 as notesheets_received,
                        0 as bills_received,
                        COUNT(*) as letters_received,
                        0 as notesheets_cleared,
                        0 as bills_paid,
                        SUM(CASE WHEN current_status = 'Closed' THEN 1 ELSE 0 END) as letters_closed,
                        0 as avg_notesheet_days,
                        0 as avg_bill_days,
                        AVG(julianday('now') - julianday(received_date)) as avg_letter_days
                    FROM letters
                    WHERE strftime('%Y-%m', received_date) >= strftime('%Y-%m', 'now', '-12 months')
                    GROUP BY month
                )
                GROUP BY month
                ORDER BY month DESC
                LIMIT 12
            '''
            
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            report_data = [dict(zip(columns, row)) for row in results]
        
        # Priority Analysis Report - UPDATED WITH LETTERS
        elif report_type == 'priority_analysis':
            query = '''
                SELECT 
                    priority,
                    'Notesheet' as doc_type,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN is_parked = 0 AND current_status != 'Closed' THEN 1 ELSE 0 END) as active_count,
                    SUM(CASE WHEN is_parked = 1 THEN 1 ELSE 0 END) as parked_count,
                    AVG(julianday('now') - julianday(received_date)) as avg_age_days
                FROM notesheets
                GROUP BY priority
                UNION ALL
                SELECT 
                    priority,
                    'Bill' as doc_type,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN is_parked = 0 AND payment_status = 'Pending' THEN 1 ELSE 0 END) as active_count,
                    SUM(CASE WHEN is_parked = 1 THEN 1 ELSE 0 END) as parked_count,
                    AVG(julianday('now') - julianday(received_date)) as avg_age_days
                FROM bills
                GROUP BY priority
                UNION ALL
                SELECT 
                    priority,
                    'Letter' as doc_type,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN is_parked = 0 AND current_status NOT IN ('Closed', 'Replied') THEN 1 ELSE 0 END) as active_count,
                    SUM(CASE WHEN is_parked = 1 THEN 1 ELSE 0 END) as parked_count,
                    AVG(julianday('now') - julianday(received_date)) as avg_age_days
                FROM letters
                GROUP BY priority
                ORDER BY priority, doc_type
            '''
            
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            report_data = [dict(zip(columns, row)) for row in results]
        
        # SLA Compliance Report - UPDATED WITH LETTERS
        elif report_type == 'sla_compliance':
            # Define SLA limits (in days)
            SLA_LIMITS = {
                'Urgent': 2,
                'High': 5,
                'Normal': 10
            }
            
            report_data = []
            
            for priority, sla_days in SLA_LIMITS.items():
                # Notesheets - using received_date since no movement date available
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE 
                            WHEN CAST(julianday('now') - julianday(received_date) AS INTEGER) <= ? 
                            THEN 1 ELSE 0 
                        END) as within_sla,
                        SUM(CASE 
                            WHEN CAST(julianday('now') - julianday(received_date) AS INTEGER) > ? 
                            THEN 1 ELSE 0 
                        END) as breached_sla
                    FROM notesheets
                    WHERE priority = ? AND is_parked = 0 AND current_holder IS NOT NULL
                ''', (sla_days, sla_days, priority))
                
                ns_result = cursor.fetchone()
                
                if ns_result and ns_result[0] > 0:
                    compliance = (ns_result[1] / ns_result[0]) * 100 if ns_result[0] > 0 else 0
                    report_data.append({
                        'priority': priority,
                        'doc_type': 'Notesheet',
                        'sla_days': sla_days,
                        'total_docs': ns_result[0],
                        'within_sla': ns_result[1],
                        'breached_sla': ns_result[2],
                        'compliance_percent': round(compliance, 1)
                    })
                
                # Bills
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE 
                            WHEN CAST(julianday('now') - julianday(received_date) AS INTEGER) <= ? 
                            THEN 1 ELSE 0 
                        END) as within_sla,
                        SUM(CASE 
                            WHEN CAST(julianday('now') - julianday(received_date) AS INTEGER) > ? 
                            THEN 1 ELSE 0 
                        END) as breached_sla
                    FROM bills
                    WHERE priority = ? AND is_parked = 0 AND current_holder IS NOT NULL
                ''', (sla_days, sla_days, priority))
                
                bill_result = cursor.fetchone()
                
                if bill_result and bill_result[0] > 0:
                    compliance = (bill_result[1] / bill_result[0]) * 100 if bill_result[0] > 0 else 0
                    report_data.append({
                        'priority': priority,
                        'doc_type': 'Bill',
                        'sla_days': sla_days,
                        'total_docs': bill_result[0],
                        'within_sla': bill_result[1],
                        'breached_sla': bill_result[2],
                        'compliance_percent': round(compliance, 1)
                    })
                
                # Letters - NEW!
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE 
                            WHEN CAST(julianday('now') - julianday(received_date) AS INTEGER) <= ? 
                            THEN 1 ELSE 0 
                        END) as within_sla,
                        SUM(CASE 
                            WHEN CAST(julianday('now') - julianday(received_date) AS INTEGER) > ? 
                            THEN 1 ELSE 0 
                        END) as breached_sla
                    FROM letters
                    WHERE priority = ? AND is_parked = 0 AND current_holder IS NOT NULL
                ''', (sla_days, sla_days, priority))
                
                letter_result = cursor.fetchone()
                
                if letter_result and letter_result[0] > 0:
                    compliance = (letter_result[1] / letter_result[0]) * 100 if letter_result[0] > 0 else 0
                    report_data.append({
                        'priority': priority,
                        'doc_type': 'Letter',
                        'sla_days': sla_days,
                        'total_docs': letter_result[0],
                        'within_sla': letter_result[1],
                        'breached_sla': letter_result[2],
                        'compliance_percent': round(compliance, 1)
                    })
    
    db.close()
    
    return render_template('advanced_reports.html',
                         report_type=report_type,
                         report_data=report_data,
                         aging_summary=aging_summary,
                         date_from=date_from,
                         date_to=date_to)

# Notesheet routes

@app.route('/notesheets')
@login_required
def notesheets_list():
    """List all notesheets"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get search and filter parameters
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    # Build query with section info
    query = '''
        SELECT 
            n.notesheet_id, n.notesheet_number, n.subject, n.sender_name,
            n.received_date, n.current_status, n.priority, n.is_parked,
            u.full_name as current_holder_name,
            s.section_name as current_section_name
        FROM notesheets n
        LEFT JOIN users u ON n.current_holder = u.user_id
        LEFT JOIN sections s ON n.current_section_id = s.section_id
        WHERE 1=1
    '''
    params = []
    
    if search:
        query += ' AND (n.notesheet_number LIKE ? OR n.subject LIKE ? OR n.sender_name LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param])
    
    if status:
        query += ' AND n.current_status = ?'
        params.append(status)
    
    query += ' ORDER BY n.received_date DESC'
    
    cursor.execute(query, params)
    notesheets = cursor.fetchall()
    
    # Convert to list of dicts
    columns = [desc[0] for desc in cursor.description]
    notesheets = [dict(zip(columns, row)) for row in notesheets]
    
    db.close()
    
    return render_template('notesheets/list.html', notesheets=notesheets)

@app.route('/notesheets/<int:notesheet_id>')
@login_required
def notesheet_detail(notesheet_id):
    """View notesheet details"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get notesheet details with section info and time tracking
    cursor.execute('''
        SELECT 
            n.*,
            u1.full_name as current_holder_name,
            u2.full_name as received_by_name,
            s.section_name as current_section_name,
            ss.sub_section_name as current_sub_section_name,
            CAST((julianday('now') - julianday(
                (SELECT forwarded_date FROM notesheet_movements 
                 WHERE notesheet_id = n.notesheet_id AND is_current = 1 
                 ORDER BY forwarded_date DESC LIMIT 1)
            )) AS INTEGER) as days_held,
            CAST((julianday('now') - julianday(
                (SELECT forwarded_date FROM notesheet_movements 
                 WHERE notesheet_id = n.notesheet_id AND is_current = 1 
                 ORDER BY forwarded_date DESC LIMIT 1)
            )) * 24 AS INTEGER) as hours_held
        FROM notesheets n
        LEFT JOIN users u1 ON n.current_holder = u1.user_id
        LEFT JOIN users u2 ON n.received_by = u2.user_id
        LEFT JOIN sections s ON n.current_section_id = s.section_id
        LEFT JOIN sub_sections ss ON n.current_sub_section_id = ss.sub_section_id
        WHERE n.notesheet_id = ?
    ''', (notesheet_id,))
    
    notesheet = cursor.fetchone()
    
    if not notesheet:
        db.close()
        flash('Notesheet not found.', 'error')
        return redirect(url_for('notesheets_list'))
    
    # Convert to dict
    columns = [desc[0] for desc in cursor.description]
    notesheet = dict(zip(columns, notesheet))
    
    # === COMPREHENSIVE DEBUG ===
    print("=" * 80)
    print(f"NOTESHEET #{notesheet_id} DETAIL - COMPREHENSIVE DEBUG")
    print("=" * 80)
    print(f"Current User: ID={current_user.id}, Username={current_user.username}")
    print(f"Current User Section ID: {current_user.section_id}")
    print(f"Is Section Head: {current_user.is_section_head()}")
    print(f"Is Receive Section: {current_user.is_receive_section()}")
    print(f"Is Superuser: {current_user.is_superuser}")
    print(f"Notesheet Current Holder: {notesheet['current_holder']}")
    print(f"Holder matches current user: {notesheet['current_holder'] == current_user.id}")
    print("=" * 80)
    
    # Get movement history with section info (newest first - DESC)
    cursor.execute('''
        SELECT 
            nm.*,
            u1.full_name as from_user_name,
            u2.full_name as to_user_name,
            u3.full_name as forwarded_by_name,
            s1.section_name as from_section_name,
            s2.section_name as to_section_name,
            DATE(nm.forwarded_date) as forward_date_only
        FROM notesheet_movements nm
        LEFT JOIN users u1 ON nm.from_user = u1.user_id
        LEFT JOIN users u2 ON nm.to_user = u2.user_id
        LEFT JOIN users u3 ON nm.forwarded_by = u3.user_id
        LEFT JOIN sections s1 ON nm.from_section_id = s1.section_id
        LEFT JOIN sections s2 ON nm.to_section_id = s2.section_id
        WHERE nm.notesheet_id = ?
        ORDER BY nm.movement_id DESC
    ''', (notesheet_id,))
    
    movements = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    movements = [dict(zip(columns, row)) for row in movements]
    
    # Calculate days held - CORRECTED
    # movements[0] = newest (current), movements[-1] = oldest (initial receipt)
    from datetime import datetime as dt
    for i, movement in enumerate(movements):
        movement['display_date'] = movement['forward_date_only']
        
        if i == 0:
            # Current/newest location - still here
            try:
                in_date = dt.strptime(movement['forward_date_only'], '%Y-%m-%d').date()
                today = dt.now().date()
                days_diff = (today - in_date).days
                
                movement['in_date'] = movement['forward_date_only']
                movement['out_date'] = 'Present'
                
                if days_diff == 0:
                    movement['time_held'] = "Today (current)"
                elif days_diff == 1:
                    movement['time_held'] = "1 day (current)"
                else:
                    movement['time_held'] = f"{days_diff} days (current)"
            except:
                movement['time_held'] = "Unknown (current)"
        elif i == len(movements) - 1:
            # Oldest movement (initial receipt) - always calculate OUT to next movement
            movement['in_date'] = movement['forward_date_only']
            if len(movements) > 1:
                # There IS a next movement - calculate OUT date
                try:
                    in_date_str = movement['forward_date_only']
                    out_date_str = movements[i-1]['forward_date_only']
                    
                    # Handle None values
                    if not in_date_str or not out_date_str:
                        movement['out_date'] = 'N/A'
                        movement['time_held'] = "Missing date"
                    else:
                        in_date = dt.strptime(str(in_date_str), '%Y-%m-%d').date()
                        out_date = dt.strptime(str(out_date_str), '%Y-%m-%d').date()
                        days_diff = (out_date - in_date).days
                        
                        movement['out_date'] = out_date_str
                        
                        if days_diff < 0:
                            movement['time_held'] = f"{abs(days_diff)} days (ERROR: OUT before IN)"
                        elif days_diff == 0:
                            movement['time_held'] = "Same day"
                        elif days_diff == 1:
                            movement['time_held'] = "1 day"
                        else:
                            movement['time_held'] = f"{days_diff} days"
                except Exception as e:
                    # Even on error, set OUT date if available
                    if i > 0 and movements[i-1].get('forward_date_only'):
                        movement['out_date'] = movements[i-1]['forward_date_only']
                    else:
                        movement['out_date'] = 'N/A'
                    movement['time_held'] = f"Error: {str(e)[:30]}"
            else:
                # Only one movement - still at initial receipt
                movement['out_date'] = 'Present'
                movement['time_held'] = "Still here (current)"
        else:
            # Middle movements - calculate time from IN to next movement
            try:
                in_date = dt.strptime(movement['forward_date_only'], '%Y-%m-%d').date()
                out_date = dt.strptime(movements[i-1]['forward_date_only'], '%Y-%m-%d').date()
                days_diff = (out_date - in_date).days
                
                movement['in_date'] = movement['forward_date_only']
                movement['out_date'] = movements[i-1]['forward_date_only']
                
                if days_diff < 0:
                    # Negative days - data issue, don't show OUT
                    movement['out_date'] = 'N/A'
                    movement['time_held'] = "Data error"
                elif days_diff == 0:
                    movement['time_held'] = "Same day"
                elif days_diff == 1:
                    movement['time_held'] = "1 day"
                else:
                    movement['time_held'] = f"{days_diff} days"
            except:
                movement['time_held'] = "Unknown"
    
    # Get sections for forwarding dropdown
    sections = db.get_all_sections()
    
    # Determine who can forward based on role
    can_forward = False
    users = []
    
    # Get the current holder ID to exclude from dropdown
    current_holder_id = notesheet['current_holder']
    
    if current_user.is_receive_section():
        # Receive section can ALWAYS forward to any section, regardless of current holder
        # Exclude current holder and superusers from list
        can_forward = True
        cursor.execute('''
            SELECT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            WHERE u.is_active = 1 
            AND u.user_id != ?
            AND u.is_superuser = 0
            ORDER BY s.section_name, u.full_name
        ''', (current_holder_id,))
        
    elif current_user.is_section_head() and notesheet['current_holder'] == current_user.id:
        # Section heads can forward if they are the current holder
        # Can forward to:
        # 1. Users in their own section (excluding themselves)
        # 2. Other section heads
        # 3. Receive section users
        can_forward = True
        
        print(f"DEBUG NOTESHEET: User ID={current_user.id}, Section ID={current_user.section_id}")
        
        cursor.execute('''
            SELECT DISTINCT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
            LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
            WHERE u.is_active = 1 
            AND u.user_id != ?
            AND u.is_superuser = 0
            AND (
                u.section_id = ?
                OR ur.role_name = 'section_head'
                OR ur.role_name = 'receive_section'
            )
            ORDER BY s.section_name, u.full_name
        ''', (current_user.id, current_user.section_id))
        
        test_users = cursor.fetchall()
        print(f"DEBUG NOTESHEET: Query returned {len(test_users)} users")
        for usr in test_users:
            print(f"DEBUG NOTESHEET:   {usr}")
        
        # Reset cursor for actual use
        cursor.execute('''
            SELECT DISTINCT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
            LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
            WHERE u.is_active = 1 
            AND u.user_id != ?
            AND u.is_superuser = 0
            AND (
                u.section_id = ?
                OR ur.role_name = 'section_head'
                OR ur.role_name = 'receive_section'
            )
            ORDER BY s.section_name, u.full_name
        ''', (current_user.id, current_user.section_id))
        
    elif notesheet['current_holder'] == current_user.id:
        # Sectional users (section_member) can forward to their section head
        can_forward = True
        cursor.execute('''
            SELECT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
            LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
            WHERE u.is_active = 1 
            AND u.section_id = ?
            AND ur.role_name = 'section_head'
            AND u.user_id != ?
            AND u.is_superuser = 0
            ORDER BY u.full_name
        ''', (current_user.section_id, current_user.id))
    
    users = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    users = [dict(zip(columns, row)) for row in users]
    
    # === FINAL DEBUG: Users being sent to template ===
    print(f"\n>>> FINAL NOTESHEET: Sending {len(users)} users to template")
    for user in users:
        print(f"    User ID={user['user_id']}, Name={user['full_name']}, Section={user.get('section_name', 'N/A')}")
    print(f">>> can_forward={can_forward}")
    print("=" * 80 + "\n")
    
    db.close()
    
    return render_template('notesheets/detail.html', 
                         notesheet=notesheet, 
                         movements=movements, 
                         users=users,
                         sections=sections,
                         can_forward=can_forward)

@app.route('/notesheets/receive', methods=['GET', 'POST'])
@login_required
@receive_permission_required
def receive_notesheet():
    """Receive a new notesheet"""
    if request.method == 'POST':
        db = WBSEDCLDatabase()
        
        notesheet_data = {
            'notesheet_number': request.form.get('notesheet_number'),
            'subject': request.form.get('subject'),
            'sender_name': request.form.get('sender_name'),
            'sender_organization': request.form.get('sender_organization'),
            'sender_address': request.form.get('sender_address'),
            'reference_number': request.form.get('reference_number'),
            'received_date': request.form.get('received_date'),
            'category': request.form.get('category'),
            'priority': request.form.get('priority', 'Normal'),
            'remarks': request.form.get('remarks'),
            'received_by': current_user.id,
            'current_section_id': current_user.section_id or 1
        }
        
        notesheet_id = db.create_notesheet(notesheet_data)
        
        if notesheet_id:
            db.log_activity(current_user.id, 'notesheet_received', 
                          f"Received notesheet: {notesheet_data['notesheet_number']}", 
                          request.remote_addr)
            flash('Notesheet received successfully!', 'success')
            db.close()
            return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
        else:
            db.close()
            flash('Failed to receive notesheet.', 'error')
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('notesheets/receive.html', today=today)

@app.route('/notesheets/<int:notesheet_id>/forward', methods=['POST'])
@login_required
def forward_notesheet_route(notesheet_id):
    """Forward a notesheet to another user"""
    
    # Permission check first
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get notesheet info
    cursor.execute('''
        SELECT current_holder, current_status 
        FROM notesheets 
        WHERE notesheet_id = ?
    ''', (notesheet_id,))
    
    notesheet = cursor.fetchone()
    
    if not notesheet:
        flash('Notesheet not found.', 'error')
        db.close()
        return redirect(url_for('notesheets_list'))
    
    current_holder, current_status = notesheet
    
    # PERMISSION CHECK
    can_forward = (
        current_holder == current_user.id or
        current_user.is_receive_section() or
        current_user.is_section_head() or
        current_user.is_superuser
    )
    
    if not can_forward:
        flash('You do not have permission to forward this document.', 'error')
        db.close()
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    # Cannot forward if closed/archived
    if current_status in ['Closed', 'Archived']:
        flash('Cannot forward closed or archived documents.', 'error')
        db.close()
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    db.close()
    
    # Get form data
    to_user = request.form.get('to_user')
    action = request.form.get('action', 'Forwarded')
    comments = request.form.get('comments')
    forward_date = request.form.get('forward_date')
    
    if not to_user:
        flash('Please select a user to forward to.', 'error')
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    if not forward_date:
        flash('Please provide forward date.', 'error')
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    # Validate forward date
    from datetime import datetime
    try:
        forward_date_obj = datetime.strptime(forward_date, '%Y-%m-%d')
        if forward_date_obj > datetime.now():
            flash('Forward date cannot be in the future.', 'error')
            return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    # Use existing database method
    db = WBSEDCLDatabase()
    
    movement_data = {
        'notesheet_id': notesheet_id,
        'from_user': current_user.id,
        'to_user': int(to_user),
        'forwarded_by': current_user.id,
        'action_taken': action,
        'comments': comments,
        'forward_date': forward_date
    }
    
    success = db.forward_notesheet(movement_data)
    
    if success:
        db.log_activity(current_user.id, 'notesheet_forwarded',
                       f"Forwarded notesheet ID {notesheet_id} to user ID {to_user} on {forward_date}",
                       request.remote_addr)
        flash('Notesheet forwarded successfully!', 'success')
    else:
        flash('Failed to forward notesheet.', 'error')
    
    db.close()
    return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))

@app.route('/notesheets/<int:notesheet_id>/park', methods=['POST'])
@login_required
@receive_permission_required
def park_notesheet_route(notesheet_id):
    """Park a notesheet in Receive Section"""
    reason = request.form.get('reason')
    comments = request.form.get('comments')
    
    if not reason:
        flash('Please provide a reason for parking.', 'error')
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    db = WBSEDCLDatabase()
    success = db.park_notesheet(notesheet_id, current_user.id, reason, comments)
    
    if success:
        db.log_activity(current_user.id, 'notesheet_parked',
                       f"Parked notesheet ID {notesheet_id}",
                       request.remote_addr)
        flash('Notesheet parked successfully!', 'success')
    else:
        flash('Failed to park notesheet.', 'error')
    
    db.close()
    return redirect(url_for('notesheets_list'))

@app.route('/notesheets/parked')
@login_required
@receive_permission_required
def parked_notesheets():
    """View all parked notesheets"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            n.*,
            u.full_name as parked_by_name,
            CAST((julianday('now') - julianday(n.parked_date)) AS INTEGER) as days_parked
        FROM notesheets n
        LEFT JOIN users u ON n.parked_by = u.user_id
        WHERE n.is_parked = 1
        ORDER BY n.parked_date DESC
    ''')
    
    parked = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    parked = [dict(zip(columns, row)) for row in parked]
    
    db.close()
    
    return render_template('notesheets/parked.html', parked=parked)

# Bill routes

@app.route('/bills')
@login_required
def bills_list():
    """List all bills"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get search and filter parameters
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    # Build query with section info
    query = '''
        SELECT 
            b.bill_id, b.bill_number, b.invoice_number, b.vendor_name,
            b.bill_amount, b.received_date, b.current_status, b.payment_status, b.priority,
            u.full_name as current_holder_name,
            s.section_name as current_section_name
        FROM bills b
        LEFT JOIN users u ON b.current_holder = u.user_id
        LEFT JOIN sections s ON b.current_section_id = s.section_id
        WHERE 1=1
    '''
    params = []
    
    if search:
        query += ' AND (b.bill_number LIKE ? OR b.vendor_name LIKE ? OR b.invoice_number LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param])
    
    if status:
        query += ' AND b.current_status = ?'
        params.append(status)
    
    query += ' ORDER BY b.received_date DESC'
    
    cursor.execute(query, params)
    bills = cursor.fetchall()
    
    # Convert to list of dicts
    columns = [desc[0] for desc in cursor.description]
    bills = [dict(zip(columns, row)) for row in bills]
    
    db.close()
    
    return render_template('bills/list.html', bills=bills)

@app.route('/bills/<int:bill_id>')
@login_required
def bill_detail(bill_id):
    """View bill details"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get bill details with section info and time tracking
    cursor.execute('''
        SELECT 
            b.*,
            u1.full_name as current_holder_name,
            u2.full_name as received_by_name,
            s.section_name as current_section_name,
            ss.sub_section_name as current_sub_section_name,
            CAST((julianday('now') - julianday(
                (SELECT forwarded_date FROM bill_movements 
                 WHERE bill_id = b.bill_id AND is_current = 1 
                 ORDER BY forwarded_date DESC LIMIT 1)
            )) AS INTEGER) as days_held,
            CAST((julianday('now') - julianday(
                (SELECT forwarded_date FROM bill_movements 
                 WHERE bill_id = b.bill_id AND is_current = 1 
                 ORDER BY forwarded_date DESC LIMIT 1)
            )) * 24 AS INTEGER) as hours_held
        FROM bills b
        LEFT JOIN users u1 ON b.current_holder = u1.user_id
        LEFT JOIN users u2 ON b.received_by = u2.user_id
        LEFT JOIN sections s ON b.current_section_id = s.section_id
        LEFT JOIN sub_sections ss ON b.current_sub_section_id = ss.sub_section_id
        WHERE b.bill_id = ?
    ''', (bill_id,))
    
    bill = cursor.fetchone()
    
    if not bill:
        db.close()
        flash('Bill not found.', 'error')
        return redirect(url_for('bills_list'))
    
    # Convert to dict
    columns = [desc[0] for desc in cursor.description]
    bill = dict(zip(columns, bill))
    
    # Get movement history with section info (newest first - DESC)
    cursor.execute('''
        SELECT 
            bm.*,
            u1.full_name as from_user_name,
            u2.full_name as to_user_name,
            u3.full_name as forwarded_by_name,
            s1.section_name as from_section_name,
            s2.section_name as to_section_name,
            DATE(bm.forwarded_date) as forward_date_only
        FROM bill_movements bm
        LEFT JOIN users u1 ON bm.from_user = u1.user_id
        LEFT JOIN users u2 ON bm.to_user = u2.user_id
        LEFT JOIN users u3 ON bm.forwarded_by = u3.user_id
        LEFT JOIN sections s1 ON bm.from_section_id = s1.section_id
        LEFT JOIN sections s2 ON bm.to_section_id = s2.section_id
        WHERE bm.bill_id = ?
        ORDER BY bm.movement_id DESC
    ''', (bill_id,))
    
    movements = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    movements = [dict(zip(columns, row)) for row in movements]
    
    # Calculate days held - CORRECTED
    # movements[0] = newest (current), movements[-1] = oldest (initial receipt)
    from datetime import datetime as dt
    for i, movement in enumerate(movements):
        movement['display_date'] = movement['forward_date_only']
        
        if i == 0:
            # Current/newest location - still here
            try:
                in_date = dt.strptime(movement['forward_date_only'], '%Y-%m-%d').date()
                today = dt.now().date()
                days_diff = (today - in_date).days
                
                movement['in_date'] = movement['forward_date_only']
                movement['out_date'] = 'Present'
                
                if days_diff == 0:
                    movement['time_held'] = "Today (current)"
                elif days_diff == 1:
                    movement['time_held'] = "1 day (current)"
                else:
                    movement['time_held'] = f"{days_diff} days (current)"
            except:
                movement['time_held'] = "Unknown (current)"
        elif i == len(movements) - 1:
            # Oldest movement (initial receipt) - always calculate OUT to next movement
            movement['in_date'] = movement['forward_date_only']
            if len(movements) > 1:
                # There IS a next movement - calculate OUT date
                try:
                    in_date_str = movement['forward_date_only']
                    out_date_str = movements[i-1]['forward_date_only']
                    
                    # Handle None values
                    if not in_date_str or not out_date_str:
                        movement['out_date'] = 'N/A'
                        movement['time_held'] = "Missing date"
                    else:
                        in_date = dt.strptime(str(in_date_str), '%Y-%m-%d').date()
                        out_date = dt.strptime(str(out_date_str), '%Y-%m-%d').date()
                        days_diff = (out_date - in_date).days
                        
                        movement['out_date'] = out_date_str
                        
                        if days_diff < 0:
                            movement['time_held'] = f"{abs(days_diff)} days (ERROR: OUT before IN)"
                        elif days_diff == 0:
                            movement['time_held'] = "Same day"
                        elif days_diff == 1:
                            movement['time_held'] = "1 day"
                        else:
                            movement['time_held'] = f"{days_diff} days"
                except Exception as e:
                    # Even on error, set OUT date if available
                    if i > 0 and movements[i-1].get('forward_date_only'):
                        movement['out_date'] = movements[i-1]['forward_date_only']
                    else:
                        movement['out_date'] = 'N/A'
                    movement['time_held'] = f"Error: {str(e)[:30]}"
            else:
                # Only one movement - still at initial receipt
                movement['out_date'] = 'Present'
                movement['time_held'] = "Still here (current)"
        else:
            # Middle movements - calculate time from IN to next movement
            try:
                in_date = dt.strptime(movement['forward_date_only'], '%Y-%m-%d').date()
                out_date = dt.strptime(movements[i-1]['forward_date_only'], '%Y-%m-%d').date()
                days_diff = (out_date - in_date).days
                
                movement['in_date'] = movement['forward_date_only']
                movement['out_date'] = movements[i-1]['forward_date_only']
                
                if days_diff < 0:
                    # Negative days - data issue, don't show OUT
                    movement['out_date'] = 'N/A'
                    movement['time_held'] = "Data error"
                elif days_diff == 0:
                    movement['time_held'] = "Same day"
                elif days_diff == 1:
                    movement['time_held'] = "1 day"
                else:
                    movement['time_held'] = f"{days_diff} days"
            except:
                movement['time_held'] = "Unknown"
    
    # Get sections for forwarding dropdown
    sections = db.get_all_sections()
    
    # Determine who can forward based on role
    can_forward = False
    users = []
    
    # Get the current holder ID to exclude from dropdown
    current_holder_id = bill['current_holder']
    
    if current_user.is_receive_section():
        # Receive section can ALWAYS forward to any section, regardless of current holder
        # Exclude current holder and superusers from list
        can_forward = True
        cursor.execute('''
            SELECT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            WHERE u.is_active = 1 
            AND u.user_id != ?
            AND u.is_superuser = 0
            ORDER BY s.section_name, u.full_name
        ''', (current_holder_id,))
        
    elif current_user.is_section_head() and bill['current_holder'] == current_user.id:
        # Section heads can forward if they are the current holder
        # Can forward to:
        # 1. Users in their own section (excluding themselves)
        # 2. Other section heads
        # 3. Receive section users
        can_forward = True
        
        print(f"DEBUG BILL: User ID={current_user.id}, Section ID={current_user.section_id}")
        
        cursor.execute('''
            SELECT DISTINCT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
            LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
            WHERE u.is_active = 1 
            AND u.user_id != ?
            AND u.is_superuser = 0
            AND (
                u.section_id = ?
                OR ur.role_name = 'section_head'
                OR ur.role_name = 'receive_section'
            )
            ORDER BY s.section_name, u.full_name
        ''', (current_user.id, current_user.section_id))
        
        test_users = cursor.fetchall()
        print(f"DEBUG BILL: Query returned {len(test_users)} users")
        for usr in test_users:
            print(f"DEBUG BILL:   {usr}")
        
        # Reset cursor for actual use
        cursor.execute('''
            SELECT DISTINCT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
            LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
            WHERE u.is_active = 1 
            AND u.user_id != ?
            AND u.is_superuser = 0
            AND (
                u.section_id = ?
                OR ur.role_name = 'section_head'
                OR ur.role_name = 'receive_section'
            )
            ORDER BY s.section_name, u.full_name
        ''', (current_user.id, current_user.section_id))
        
    elif bill['current_holder'] == current_user.id:
        # Sectional users (section_member) can forward to their section head
        can_forward = True
        cursor.execute('''
            SELECT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
            LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
            WHERE u.is_active = 1 
            AND u.section_id = ?
            AND ur.role_name = 'section_head'
            AND u.user_id != ?
            AND u.is_superuser = 0
            ORDER BY u.full_name
        ''', (current_user.section_id, current_user.id))
    
    users = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    users = [dict(zip(columns, row)) for row in users]
    
    db.close()
    
    return render_template('bills/detail.html', 
                         bill=bill, 
                         movements=movements, 
                         users=users,
                         sections=sections,
                         can_forward=can_forward)

@app.route('/bills/receive', methods=['GET', 'POST'])
@login_required
@receive_permission_required
def receive_bill():
    """Receive a new bill"""
    if request.method == 'POST':
        db = WBSEDCLDatabase()
        
        bill_data = {
            'bill_number': request.form.get('bill_number'),
            'invoice_number': request.form.get('invoice_number'),
            'vendor_name': request.form.get('vendor_name'),
            'vendor_address': request.form.get('vendor_address'),
            'vendor_gstin': request.form.get('vendor_gstin'),
            'vendor_pan': request.form.get('vendor_pan'),
            'bill_date': request.form.get('bill_date'),
            'received_date': request.form.get('received_date'),
            'bill_amount': float(request.form.get('bill_amount') or 0) if request.form.get('bill_amount') else 0.0,
            'taxable_amount': float(request.form.get('taxable_amount') or 0) if request.form.get('taxable_amount') else None,
            'gst_amount': float(request.form.get('gst_amount') or 0) if request.form.get('gst_amount') else None,
            'tds_amount': float(request.form.get('tds_amount') or 0) if request.form.get('tds_amount') else None,
            'net_payable_amount': float(request.form.get('net_payable_amount') or 0) if request.form.get('net_payable_amount') else None,
            'bill_type': request.form.get('bill_type'),
            'category': request.form.get('category'),
            'priority': request.form.get('priority', 'Normal'),
            'description': request.form.get('description'),
            'remarks': request.form.get('remarks'),
            'received_by': current_user.id,
            'current_section_id': current_user.section_id or 1
        }
        
        bill_id = db.create_bill(bill_data)
        
        if bill_id:
            db.log_activity(current_user.id, 'bill_received',
                          f"Received bill: {bill_data['bill_number']}",
                          request.remote_addr)
            flash('Bill received successfully!', 'success')
            db.close()
            return redirect(url_for('bill_detail', bill_id=bill_id))
        else:
            db.close()
            flash('Failed to receive bill.', 'error')
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('bills/receive.html', today=today)

@app.route('/bills/<int:bill_id>/forward', methods=['POST'])
@login_required
def forward_bill_route(bill_id):
    """Forward a bill to another user"""
    
    # Permission check first
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get bill info
    cursor.execute('''
        SELECT current_holder, current_status, payment_status
        FROM bills 
        WHERE bill_id = ?
    ''', (bill_id,))
    
    bill = cursor.fetchone()
    
    if not bill:
        flash('Bill not found.', 'error')
        db.close()
        return redirect(url_for('bills_list'))
    
    current_holder, current_status, payment_status = bill
    
    # PERMISSION CHECK
    can_forward = (
        current_holder == current_user.id or
        current_user.is_receive_section() or
        current_user.is_section_head() or
        current_user.is_superuser
    )
    
    if not can_forward:
        flash('You do not have permission to forward this document.', 'error')
        db.close()
        return redirect(url_for('bill_detail', bill_id=bill_id))
    
    # Cannot forward if closed/archived/paid
    if current_status in ['Closed', 'Archived'] or payment_status == 'Paid':
        flash('Cannot forward closed, archived, or paid bills.', 'error')
        db.close()
        return redirect(url_for('bill_detail', bill_id=bill_id))
    
    db.close()
    
    # Get form data
    to_user = request.form.get('to_user')
    action = request.form.get('action', 'Forwarded')
    comments = request.form.get('comments')
    forward_date = request.form.get('forward_date')
    
    if not to_user:
        flash('Please select a user to forward to.', 'error')
        return redirect(url_for('bill_detail', bill_id=bill_id))
    
    if not forward_date:
        flash('Please provide forward date.', 'error')
        return redirect(url_for('bill_detail', bill_id=bill_id))
    
    # Validate forward date
    from datetime import datetime
    try:
        forward_date_obj = datetime.strptime(forward_date, '%Y-%m-%d')
        if forward_date_obj > datetime.now():
            flash('Forward date cannot be in the future.', 'error')
            return redirect(url_for('bill_detail', bill_id=bill_id))
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('bill_detail', bill_id=bill_id))
    
    # Use existing database method
    db = WBSEDCLDatabase()
    
    movement_data = {
        'bill_id': bill_id,
        'from_user': current_user.id,
        'to_user': int(to_user),
        'forwarded_by': current_user.id,
        'action_taken': action,
        'comments': comments,
        'forward_date': forward_date
    }
    
    success = db.forward_bill(movement_data)
    
    if success:
        db.log_activity(current_user.id, 'bill_forwarded',
                       f"Forwarded bill ID {bill_id} to user ID {to_user} on {forward_date}",
                       request.remote_addr)
        flash('Bill forwarded successfully!', 'success')
    else:
        flash('Failed to forward bill.', 'error')
    
    db.close()
    return redirect(url_for('bill_detail', bill_id=bill_id))



# =============================================================================
# LETTER ROUTES - ADD TO app.py AFTER BILL ROUTES (around line 1400)
# =============================================================================

# Letter routes

@app.route('/letters')
@login_required
def letters_list():
    """List all letters"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get search and filter parameters
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    # Build query with section info
    query = '''
        SELECT 
            l.letter_id, l.letter_number, l.subject, l.sender_name,
            l.received_date, l.current_status, l.priority, l.is_parked,
            l.letter_type, l.reply_required,
            u.full_name as current_holder_name,
            s.section_name as current_section_name
        FROM letters l
        LEFT JOIN users u ON l.current_holder = u.user_id
        LEFT JOIN sections s ON l.current_section_id = s.section_id
        WHERE 1=1
    '''
    params = []
    
    if search:
        query += ' AND (l.letter_number LIKE ? OR l.subject LIKE ? OR l.sender_name LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param])
    
    if status:
        query += ' AND l.current_status = ?'
        params.append(status)
    
    query += ' ORDER BY l.received_date DESC'
    
    cursor.execute(query, params)
    letters = cursor.fetchall()
    
    # Convert to list of dicts
    columns = [desc[0] for desc in cursor.description]
    letters = [dict(zip(columns, row)) for row in letters]
    
    db.close()
    
    return render_template('letters/list.html', letters=letters)

@app.route('/my-letters')
@login_required
def my_letters():
    """Show letters assigned to current user"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get letters where current user is the holder
    cursor.execute('''
        SELECT 
            l.letter_id, l.letter_number, l.subject, l.sender_name,
            l.received_date, l.current_status, l.priority, l.is_parked,
            l.letter_type, l.reply_required,
            u.full_name as current_holder_name,
            s.section_name as current_section_name
        FROM letters l
        LEFT JOIN users u ON l.current_holder = u.user_id
        LEFT JOIN sections s ON l.current_section_id = s.section_id
        WHERE l.current_holder = ?
        ORDER BY l.received_date DESC
    ''', (current_user.id,))
    
    letters = cursor.fetchall()
    
    # Convert to list of dicts
    columns = [desc[0] for desc in cursor.description]
    letters = [dict(zip(columns, row)) for row in letters]
    
    db.close()
    
    return render_template('letters/list.html', letters=letters, filter_type='my')

@app.route('/letters/<int:letter_id>')
@login_required
def letter_detail(letter_id):
    """View letter details"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get letter details with section info (WITHOUT days_held calculation)
    cursor.execute('''
        SELECT 
            l.*,
            u1.full_name as current_holder_name,
            u2.full_name as received_by_name,
            s.section_name as current_section_name,
            ss.sub_section_name as current_sub_section_name
        FROM letters l
        LEFT JOIN users u1 ON l.current_holder = u1.user_id
        LEFT JOIN users u2 ON l.received_by = u2.user_id
        LEFT JOIN sections s ON l.current_section_id = s.section_id
        LEFT JOIN sub_sections ss ON l.current_sub_section_id = ss.sub_section_id
        WHERE l.letter_id = ?
    ''', (letter_id,))
    
    letter = cursor.fetchone()
    
    if not letter:
        db.close()
        flash('Letter not found.', 'error')
        return redirect(url_for('letters_list'))
    
    # Convert to dict
    columns = [desc[0] for desc in cursor.description]
    letter_dict = dict(zip(columns, letter))
    
    # CORRECTED: Calculate days held from CURRENT MOVEMENT, not received date
    cursor.execute('''
        SELECT forwarded_date
        FROM letter_movements
        WHERE letter_id = ? AND is_current = 1
        ORDER BY movement_id DESC
        LIMIT 1
    ''', (letter_id,))
    
    current_movement = cursor.fetchone()
    
    if current_movement and current_movement[0]:
        # Use the IN date from current movement
        from datetime import datetime
        in_date = datetime.strptime(current_movement[0], '%Y-%m-%d')
        now = datetime.now()
        days_held = (now - in_date).days
        letter_dict['days_held'] = days_held
    else:
        # Fallback to received date if no movement
        from datetime import datetime
        received_date = datetime.strptime(letter_dict['received_date'], '%Y-%m-%d')
        now = datetime.now()
        days_held = (now - received_date).days
        letter_dict['days_held'] = days_held
    
    # Get movement history (newest first - DESC)
    cursor.execute('''
        SELECT 
            lm.*,
            u1.full_name as from_user_name,
            u2.full_name as to_user_name,
            u3.full_name as forwarded_by_name,
            s1.section_name as from_section_name,
            s2.section_name as to_section_name,
            DATE(lm.forwarded_date) as forward_date_only
        FROM letter_movements lm
        LEFT JOIN users u1 ON lm.from_user = u1.user_id
        LEFT JOIN users u2 ON lm.to_user = u2.user_id
        LEFT JOIN users u3 ON lm.forwarded_by = u3.user_id
        LEFT JOIN sections s1 ON lm.from_section_id = s1.section_id
        LEFT JOIN sections s2 ON lm.to_section_id = s2.section_id
        WHERE lm.letter_id = ?
        ORDER BY lm.movement_id DESC
    ''', (letter_id,))
    
    movements = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    movements = [dict(zip(columns, row)) for row in movements]
    
    # Calculate days held for each movement
    from datetime import datetime as dt
    for i, movement in enumerate(movements):
        movement['display_date'] = movement['forward_date_only']
        
        if i == 0:
            # Current location - still here
            try:
                in_date = dt.strptime(movement['forward_date_only'], '%Y-%m-%d').date()
                today = dt.now().date()
                days_diff = (today - in_date).days
                
                movement['in_date'] = movement['forward_date_only']
                movement['out_date'] = 'Present'
                
                if days_diff == 0:
                    movement['time_held'] = "Today (current)"
                elif days_diff == 1:
                    movement['time_held'] = "1 day (current)"
                else:
                    movement['time_held'] = f"{days_diff} days (current)"
            except:
                movement['time_held'] = "Unknown (current)"
        elif i == len(movements) - 1:
            # Oldest movement
            movement['in_date'] = movement['forward_date_only']
            if len(movements) > 1:
                try:
                    in_date = dt.strptime(movement['forward_date_only'], '%Y-%m-%d').date()
                    out_date = dt.strptime(movements[i-1]['forward_date_only'], '%Y-%m-%d').date()
                    days_diff = (out_date - in_date).days
                    
                    movement['out_date'] = movements[i-1]['forward_date_only']
                    
                    if days_diff == 0:
                        movement['time_held'] = "Same day"
                    elif days_diff == 1:
                        movement['time_held'] = "1 day"
                    else:
                        movement['time_held'] = f"{days_diff} days"
                except:
                    movement['out_date'] = 'N/A'
                    movement['time_held'] = "Error"
            else:
                movement['out_date'] = 'Present'
                movement['time_held'] = "Still here (current)"
        else:
            # Middle movements
            try:
                in_date = dt.strptime(movement['forward_date_only'], '%Y-%m-%d').date()
                out_date = dt.strptime(movements[i-1]['forward_date_only'], '%Y-%m-%d').date()
                days_diff = (out_date - in_date).days
                
                movement['in_date'] = movement['forward_date_only']
                movement['out_date'] = movements[i-1]['forward_date_only']
                
                if days_diff == 0:
                    movement['time_held'] = "Same day"
                elif days_diff == 1:
                    movement['time_held'] = "1 day"
                else:
                    movement['time_held'] = f"{days_diff} days"
            except:
                movement['time_held'] = "Unknown"
    
    # Get sections for forwarding dropdown
    sections = db.get_all_sections()
    
    # Determine who can forward based on role
    can_forward = False
    users = []
    
    current_holder_id = letter_dict['current_holder']
    
    if current_user.is_receive_section():
        # Receive section can always forward
        can_forward = True
        cursor.execute('''
            SELECT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            WHERE u.is_active = 1 
            AND u.user_id != ?
            AND u.is_superuser = 0
            ORDER BY s.section_name, u.full_name
        ''', (current_holder_id,))
        
    elif current_user.is_section_head() and letter_dict['current_holder'] == current_user.id:
        # Section heads can forward if they are the current holder
        can_forward = True
        cursor.execute('''
            SELECT DISTINCT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
            LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
            WHERE u.is_active = 1 
            AND u.user_id != ?
            AND u.is_superuser = 0
            AND (
                u.section_id = ?
                OR ur.role_name = 'section_head'
                OR ur.role_name = 'receive_section'
            )
            ORDER BY s.section_name, u.full_name
        ''', (current_user.id, current_user.section_id))
        
    elif letter_dict['current_holder'] == current_user.id:
        # Sectional users can forward to their section head
        can_forward = True
        cursor.execute('''
            SELECT u.user_id, u.full_name, u.designation, s.section_name, u.section_id
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
            LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
            WHERE u.is_active = 1 
            AND u.section_id = ?
            AND ur.role_name = 'section_head'
            AND u.user_id != ?
            AND u.is_superuser = 0
            ORDER BY u.full_name
        ''', (current_user.section_id, current_user.id))
    
    users = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    users = [dict(zip(columns, row)) for row in users]
    
    db.close()
    
    return render_template('letters/detail.html', 
                         letter=letter_dict, 
                         movements=movements, 
                         users=users,
                         sections=sections,
                         can_forward=can_forward)



@app.route('/letters/receive', methods=['GET', 'POST'])
@login_required
@receive_permission_required
def receive_letter():
    """Receive a new letter"""
    if request.method == 'POST':
        db = WBSEDCLDatabase()
        conn = db.connect()
        cursor = conn.cursor()
        
        try:
            # Get form data
            letter_data = {
                'letter_number': request.form.get('letter_number'),
                'subject': request.form.get('subject'),
                'sender_name': request.form.get('sender_name'),
                'sender_organization': request.form.get('sender_organization'),
                'sender_address': request.form.get('sender_address'),
                'sender_email': request.form.get('sender_email'),
                'sender_phone': request.form.get('sender_phone'),
                'reference_number': request.form.get('reference_number'),
                'letter_date': request.form.get('letter_date'),
                'received_date': request.form.get('received_date'),
                'category': request.form.get('category'),
                'priority': request.form.get('priority', 'Normal'),
                'letter_type': request.form.get('letter_type', 'Incoming'),
                'reply_required': 1 if request.form.get('reply_required') else 0,
                'reply_deadline': request.form.get('reply_deadline') if request.form.get('reply_required') else None,
                'remarks': request.form.get('remarks'),
                'received_by': current_user.id,
                'current_section_id': current_user.section_id or 1
            }
            
            # Insert letter
            cursor.execute('''
                INSERT INTO letters (
                    letter_number, subject, sender_name, sender_organization,
                    sender_address, sender_email, sender_phone, reference_number,
                    letter_date, received_date, category, priority, letter_type,
                    reply_required, reply_deadline, remarks, received_by,
                    current_section_id, current_holder
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                letter_data['letter_number'], letter_data['subject'], letter_data['sender_name'],
                letter_data['sender_organization'], letter_data['sender_address'],
                letter_data['sender_email'], letter_data['sender_phone'],
                letter_data['reference_number'], letter_data['letter_date'],
                letter_data['received_date'], letter_data['category'], letter_data['priority'],
                letter_data['letter_type'], letter_data['reply_required'],
                letter_data['reply_deadline'], letter_data['remarks'],
                letter_data['received_by'], letter_data['current_section_id'],
                current_user.id
            ))
            
            letter_id = cursor.lastrowid
            
            # Create initial movement (received by current user)
            cursor.execute('''
                INSERT INTO letter_movements (
                    letter_id, to_user, to_section_id, forwarded_by,
                    forwarded_date, action_taken, is_current
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', (
                letter_id, current_user.id, current_user.section_id,
                current_user.id, letter_data['received_date'], 'Received'
            ))
            
            conn.commit()
            
            # Log activity
            db.log_activity(
                current_user.id,
                'letter_received',
                f"Received letter: {letter_data['letter_number']}",
                request.remote_addr
            )
            
            flash('Letter received successfully!', 'success')
            db.close()
            return redirect(url_for('letter_detail', letter_id=letter_id))
            
        except Exception as e:
            conn.rollback()
            db.close()
            flash(f'Error receiving letter: {str(e)}', 'error')
            return redirect(url_for('receive_letter'))
    
    # GET - show form
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('letters/receive.html', today=today)


# =============================================================================
# LETTER ROUTES - PART 2 (Forward, Park, Admin Edit)
# ADD TO app.py AFTER PART 1
# =============================================================================

@app.route('/letters/<int:letter_id>/forward', methods=['POST'])
@login_required
def forward_letter_route(letter_id):
    """Forward a letter to another user"""
    
    # Permission check first
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get letter info
    cursor.execute('''
        SELECT current_holder, current_status
        FROM letters 
        WHERE letter_id = ?
    ''', (letter_id,))
    
    letter = cursor.fetchone()
    
    if not letter:
        flash('Letter not found.', 'error')
        db.close()
        return redirect(url_for('letters_list'))
    
    current_holder, current_status = letter
    
    # PERMISSION CHECK
    can_forward = (
        current_holder == current_user.id or
        current_user.is_receive_section() or
        current_user.is_section_head() or
        current_user.is_superuser
    )
    
    if not can_forward:
        flash('You do not have permission to forward this document.', 'error')
        db.close()
        return redirect(url_for('letter_detail', letter_id=letter_id))
    
    # Cannot forward if closed/archived/replied
    if current_status in ['Closed', 'Archived', 'Replied']:
        flash('Cannot forward closed, archived, or replied letters.', 'error')
        db.close()
        return redirect(url_for('letter_detail', letter_id=letter_id))
    
    db.close()
    
    # Get form data
    to_user = request.form.get('to_user')
    action = request.form.get('action', 'Forwarded')
    comments = request.form.get('comments')
    forward_date = request.form.get('forward_date')
    
    if not to_user:
        flash('Please select a user to forward to.', 'error')
        return redirect(url_for('letter_detail', letter_id=letter_id))
    
    if not forward_date:
        flash('Please provide forward date.', 'error')
        return redirect(url_for('letter_detail', letter_id=letter_id))
    
    # Validate forward date
    from datetime import datetime
    try:
        forward_date_obj = datetime.strptime(forward_date, '%Y-%m-%d')
        if forward_date_obj > datetime.now():
            flash('Forward date cannot be in the future.', 'error')
            return redirect(url_for('letter_detail', letter_id=letter_id))
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('letter_detail', letter_id=letter_id))
    
    # Forward letter (direct SQL since there might not be a db.forward_letter method)
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    try:
        # Get to_user section
        cursor.execute('SELECT section_id FROM users WHERE user_id = ?', (to_user,))
        to_section_result = cursor.fetchone()
        to_section_id = to_section_result[0] if to_section_result else None
        
        # Set previous movements to not current (NO out_date)
        cursor.execute('''
            UPDATE letter_movements 
            SET is_current = 0
            WHERE letter_id = ? AND is_current = 1
        ''', (letter_id,))
        
        # Create new movement
        cursor.execute('''
            INSERT INTO letter_movements (
                letter_id, from_user, to_user, from_section_id, to_section_id,
                forwarded_by, forwarded_date, action_taken, comments, is_current
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            letter_id, current_holder, int(to_user), current_user.section_id, to_section_id,
            current_user.id, forward_date, action, comments
        ))
        
        # Update letter's current holder and section
        cursor.execute('''
            UPDATE letters SET 
                current_holder = ?,
                current_section_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE letter_id = ?
        ''', (int(to_user), to_section_id, letter_id))
        
        conn.commit()
        
        # Log activity
        db.log_activity(
            current_user.id,
            'letter_forwarded',
            f"Forwarded letter ID {letter_id} to user ID {to_user} on {forward_date}",
            request.remote_addr
        )
        
        flash('Letter forwarded successfully!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error forwarding letter: {str(e)}', 'error')
    
    db.close()
    return redirect(url_for('letter_detail', letter_id=letter_id))

@app.route('/letters/<int:letter_id>/park', methods=['POST'])
@login_required
@receive_permission_required
def park_letter_route(letter_id):
    """Park a letter in Receive Section"""
    reason = request.form.get('reason')
    comments = request.form.get('comments')
    
    if not reason:
        flash('Please provide a reason for parking.', 'error')
        return redirect(url_for('letter_detail', letter_id=letter_id))
    
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE letters SET
                is_parked = 1,
                parked_by = ?,
                parked_date = CURRENT_TIMESTAMP,
                parked_reason = ?,
                parked_comments = ?
            WHERE letter_id = ?
        ''', (current_user.id, reason, comments, letter_id))
        
        conn.commit()
        
        db.log_activity(
            current_user.id,
            'letter_parked',
            f"Parked letter ID {letter_id}",
            request.remote_addr
        )
        
        flash('Letter parked successfully!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error parking letter: {str(e)}', 'error')
    
    db.close()
    return redirect(url_for('letters_list'))

@app.route('/letters/parked')
@login_required
@receive_permission_required
def parked_letters():
    """View all parked letters"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            l.*,
            u.full_name as parked_by_name,
            CAST((julianday('now') - julianday(l.parked_date)) AS INTEGER) as days_parked
        FROM letters l
        LEFT JOIN users u ON l.parked_by = u.user_id
        WHERE l.is_parked = 1
        ORDER BY l.parked_date DESC
    ''')
    
    parked = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    parked = [dict(zip(columns, row)) for row in parked]
    
    db.close()
    
    return render_template('letters/parked.html', parked=parked)

# Admin Edit Routes for Letters

@app.route('/letters/<int:letter_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_letter(letter_id):
    """Edit letter - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            # Update letter
            cursor.execute('''
                UPDATE letters SET
                    letter_number = ?,
                    subject = ?,
                    sender_name = ?,
                    sender_organization = ?,
                    sender_address = ?,
                    sender_email = ?,
                    sender_phone = ?,
                    reference_number = ?,
                    letter_date = ?,
                    received_date = ?,
                    category = ?,
                    priority = ?,
                    letter_type = ?,
                    reply_required = ?,
                    reply_deadline = ?,
                    remarks = ?
                WHERE letter_id = ?
            ''', (
                request.form.get('letter_number'),
                request.form.get('subject'),
                request.form.get('sender_name'),
                request.form.get('sender_organization'),
                request.form.get('sender_address'),
                request.form.get('sender_email'),
                request.form.get('sender_phone'),
                request.form.get('reference_number'),
                request.form.get('letter_date'),
                request.form.get('received_date'),
                request.form.get('category'),
                request.form.get('priority'),
                request.form.get('letter_type'),
                1 if request.form.get('reply_required') else 0,
                request.form.get('reply_deadline') if request.form.get('reply_required') else None,
                request.form.get('remarks'),
                letter_id
            ))
            conn.commit()
            
            db.log_activity(current_user.id, 'letter_edited',
                           f"Edited letter ID {letter_id}",
                           request.remote_addr)
            
            flash('Letter updated successfully!', 'success')
            db.close()
            return redirect(url_for('letter_detail', letter_id=letter_id))
            
        except Exception as e:
            conn.rollback()
            db.close()
            flash(f'Error updating letter: {str(e)}', 'error')
            return redirect(url_for('edit_letter', letter_id=letter_id))
    
    # GET - show form
    cursor.execute('SELECT * FROM letters WHERE letter_id = ?', (letter_id,))
    letter = cursor.fetchone()
    
    if not letter:
        db.close()
        flash('Letter not found.', 'error')
        return redirect(url_for('letters_list'))
    
    columns = [desc[0] for desc in cursor.description]
    letter = dict(zip(columns, letter))
    
    db.close()
    return render_template('letters/edit.html', letter=letter)

@app.route('/movements/letter/<int:movement_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_letter_movement(movement_id):
    """Edit letter movement - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            cursor.execute('''
                UPDATE letter_movements SET
                    forwarded_date = ?,
                    comments = ?
                WHERE movement_id = ?
            ''', (
                request.form.get('forwarded_date'),
                request.form.get('comments'),
                movement_id
            ))
            conn.commit()
            
            cursor.execute('SELECT letter_id FROM letter_movements WHERE movement_id = ?', (movement_id,))
            letter_id = cursor.fetchone()[0]
            
            db.log_activity(current_user.id, 'movement_edited',
                           f"Edited letter movement ID {movement_id}",
                           request.remote_addr)
            
            flash('Movement updated successfully!', 'success')
            db.close()
            return redirect(url_for('letter_detail', letter_id=letter_id))
            
        except Exception as e:
            conn.rollback()
            db.close()
            flash(f'Error updating movement: {str(e)}', 'error')
    
    # GET - show form
    cursor.execute('''
        SELECT lm.*, l.letter_number
        FROM letter_movements lm
        JOIN letters l ON lm.letter_id = l.letter_id
        WHERE lm.movement_id = ?
    ''', (movement_id,))
    movement = cursor.fetchone()
    
    if not movement:
        db.close()
        flash('Movement not found.', 'error')
        return redirect(url_for('letters_list'))
    
    columns = [desc[0] for desc in cursor.description]
    movement = dict(zip(columns, movement))
    
    db.close()
    return render_template('letters/edit_movement.html', movement=movement)

@app.route('/movements/letter/<int:movement_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_letter_movement(movement_id):
    """Delete letter movement - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    try:
        # Get letter_id before deleting
        cursor.execute('SELECT letter_id FROM letter_movements WHERE movement_id = ?', (movement_id,))
        result = cursor.fetchone()
        
        if not result:
            db.close()
            flash('Movement not found.', 'error')
            return redirect(url_for('letters_list'))
        
        letter_id = result[0]
        
        # Delete the movement
        cursor.execute('DELETE FROM letter_movements WHERE movement_id = ?', (movement_id,))
        conn.commit()
        
        db.log_activity(current_user.id, 'movement_deleted',
                       f"Deleted letter movement ID {movement_id}",
                       request.remote_addr)
        
        flash('Movement deleted successfully!', 'success')
        db.close()
        return redirect(url_for('letter_detail', letter_id=letter_id))
        
    except Exception as e:
        conn.rollback()
        db.close()
        flash(f'Error deleting movement: {str(e)}', 'error')
        return redirect(url_for('letters_list'))
# =============================================================================
# Admin routes

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """User management page"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get all users with their roles and sections
    cursor.execute('''
        SELECT 
            u.user_id, u.username, u.full_name, u.email, 
            s.section_name, u.designation, u.is_active, u.is_superuser, u.last_login,
            GROUP_CONCAT(ur.role_name) as roles
        FROM users u
        LEFT JOIN sections s ON u.section_id = s.section_id
        LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
        LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
        GROUP BY u.user_id
        ORDER BY u.user_id
    ''')
    
    users = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    users = [dict(zip(columns, row)) for row in users]
    
    # Get all roles
    cursor.execute('SELECT * FROM user_roles ORDER BY role_id')
    roles = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    roles = [dict(zip(columns, row)) for row in roles]
    
    # Get all sections
    sections = db.get_all_sections()
    
    db.close()
    
    return render_template('admin/users.html', users=users, roles=roles, sections=sections)

# API Routes for User Management

@app.route('/api/users/create', methods=['POST'])
@login_required
@admin_required
def api_create_user():
    """API endpoint to create a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'password', 'full_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Create user in database
        db = WBSEDCLDatabase()
        
        # Check if username already exists
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE username = ?', (data['username'],))
        if cursor.fetchone():
            db.close()
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        
        # Create the user with section support
        user_id = db.create_user(
            username=data['username'],
            password=data['password'],
            full_name=data['full_name'],
            email=data.get('email'),
            phone=data.get('phone'),
            section_id=data.get('section_id'),
            sub_section_id=data.get('sub_section_id'),
            designation=data.get('designation'),
            is_section_head=data.get('is_section_head', False),
            created_by=current_user.id
        )
        
        if not user_id:
            db.close()
            return jsonify({'success': False, 'error': 'Failed to create user'}), 500
        
        # Assign roles
        roles = data.get('roles', [])
        for role_id in roles:
            db.assign_role(user_id, role_id, current_user.id)
        
        # Log activity
        db.log_activity(
            current_user.id,
            'user_created',
            f"Created new user: {data['username']}",
            request.remote_addr
        )
        
        db.close()
        
        flash(f"User '{data['username']}' created successfully!", 'success')
        return jsonify({'success': True, 'user_id': user_id, 'message': 'User created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def api_get_user(user_id):
    """API endpoint to get user details"""
    try:
        db = WBSEDCLDatabase()
        conn = db.connect()
        cursor = conn.cursor()
        
        # Get user details with roles and section
        cursor.execute('''
            SELECT 
                u.user_id, u.username, u.full_name, u.email, u.phone,
                u.section_id, s.section_name, u.designation, 
                u.is_active, u.is_superuser, u.last_login,
                GROUP_CONCAT(ur.role_name) as roles
            FROM users u
            LEFT JOIN sections s ON u.section_id = s.section_id
            LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
            LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
            WHERE u.user_id = ?
            GROUP BY u.user_id
        ''', (user_id,))
        
        user = cursor.fetchone()
        db.close()
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': {
                'user_id': user[0],
                'username': user[1],
                'full_name': user[2],
                'email': user[3],
                'phone': user[4],
                'section_id': user[5],
                'section_name': user[6],
                'designation': user[7],
                'is_active': user[8],
                'is_superuser': user[9],
                'last_login': user[10],
                'roles': user[11].split(',') if user[11] else []
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def api_toggle_user_status(user_id):
    """API endpoint to activate/deactivate user"""
    try:
        if user_id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot deactivate your own account'}), 400
        
        db = WBSEDCLDatabase()
        conn = db.connect()
        cursor = conn.cursor()
        
        # Get current status
        cursor.execute('SELECT is_active, username FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            db.close()
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        is_active, username = result
        new_status = 0 if is_active else 1
        
        # Update status
        cursor.execute('UPDATE users SET is_active = ? WHERE user_id = ?', (new_status, user_id))
        conn.commit()
        
        # Log activity
        action = 'activated' if new_status else 'deactivated'
        db.log_activity(
            current_user.id,
            'user_status_changed',
            f"{action.capitalize()} user: {username}",
            request.remote_addr
        )
        
        db.close()
        
        flash(f"User '{username}' has been {action}!", 'success')
        return jsonify({'success': True, 'is_active': new_status, 'message': f'User {action} successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        section_id = request.form.get('section_id')
        designation = request.form.get('designation')
        new_password = request.form.get('new_password')
        is_active = 1 if request.form.get('is_active') else 0
        is_superuser = 1 if request.form.get('is_superuser') else 0
        roles = request.form.getlist('roles')
        
        # Validation
        if not username or not full_name or not section_id:
            flash('Username, Full Name, and Section are required.', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        if not roles:
            flash('At least one role must be selected.', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        # Check if username already exists (for other users)
        cursor.execute('SELECT user_id FROM users WHERE username = ? AND user_id != ?', (username, user_id))
        if cursor.fetchone():
            flash(f'Username "{username}" is already taken.', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        # Prevent removing own superuser status
        if user_id == current_user.id and not is_superuser:
            flash('You cannot remove your own superuser status.', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        # Update user
        if new_password:
            # Hash the password
            import hashlib
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            cursor.execute('''
                UPDATE users SET
                    username = ?,
                    password_hash = ?,
                    full_name = ?,
                    email = ?,
                    phone = ?,
                    section_id = ?,
                    designation = ?,
                    is_active = ?,
                    is_superuser = ?
                WHERE user_id = ?
            ''', (username, password_hash, full_name, email, phone, section_id, designation, is_active, is_superuser, user_id))
        else:
            cursor.execute('''
                UPDATE users SET
                    username = ?,
                    full_name = ?,
                    email = ?,
                    phone = ?,
                    section_id = ?,
                    designation = ?,
                    is_active = ?,
                    is_superuser = ?
                WHERE user_id = ?
            ''', (username, full_name, email, phone, section_id, designation, is_active, is_superuser, user_id))
        
        # Update roles - delete old mappings and add new ones
        cursor.execute('DELETE FROM user_role_mapping WHERE user_id = ?', (user_id,))
        for role_id in roles:
            cursor.execute('''
                INSERT INTO user_role_mapping (user_id, role_id, assigned_by, assigned_at)
                VALUES (?, ?, ?, datetime('now'))
            ''', (user_id, int(role_id), current_user.id))
        
        conn.commit()
        
        # Log activity
        db.log_activity(
            current_user.id,
            'user_updated',
            f"Updated user: {username} (ID: {user_id})",
            request.remote_addr
        )
        
        db.close()
        flash(f"User '{username}' updated successfully!", 'success')
        return redirect(url_for('admin_users'))
    
    # GET - show form
    cursor.execute('''
        SELECT 
            u.user_id, u.username, u.full_name, u.email, u.phone,
            u.section_id, s.section_name, u.designation, 
            u.is_active, u.is_superuser, u.last_login,
            GROUP_CONCAT(ur.role_name) as roles
        FROM users u
        LEFT JOIN sections s ON u.section_id = s.section_id
        LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
        LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
        WHERE u.user_id = ?
        GROUP BY u.user_id
    ''', (user_id,))
    
    user = cursor.fetchone()
    
    if not user:
        db.close()
        flash('User not found.', 'error')
        return redirect(url_for('admin_users'))
    
    columns = [desc[0] for desc in cursor.description]
    user = dict(zip(columns, user))
    
    # Get all sections
    sections = db.get_all_sections()
    
    # Get all roles
    cursor.execute('SELECT * FROM user_roles ORDER BY role_id')
    all_roles = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    all_roles = [dict(zip(columns, row)) for row in all_roles]
    
    db.close()
    
    return render_template('admin/edit_user.html', 
                         user=user, 
                         sections=sections, 
                         all_roles=all_roles)

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Admin monitoring dashboard"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # System Statistics
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
    active_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 0')
    inactive_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM notesheets')
    total_notesheets = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM bills')
    total_bills = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM notesheet_movements')
    total_ns_movements = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM bill_movements')
    total_bill_movements = cursor.fetchone()[0]
    
    # Recent Activity (Last 50)
    cursor.execute('''
        SELECT 
            al.log_id,
            al.user_id,
            u.username,
            u.full_name,
            al.activity_type,
            al.description,
            al.ip_address,
            al.created_at
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.user_id
        ORDER BY al.created_at DESC
        LIMIT 50
    ''')
    activities = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    activities = [dict(zip(columns, row)) for row in activities]
    
    # Failed Login Attempts (if exists)
    try:
        cursor.execute('''
            SELECT COUNT(*) FROM activity_logs 
            WHERE activity_type = 'login_failed' 
            AND created_at >= datetime('now', '-24 hours')
        ''')
        failed_logins_24h = cursor.fetchone()[0]
    except:
        failed_logins_24h = 0
    
    # Active Sessions (users who logged in today)
    cursor.execute('''
        SELECT COUNT(DISTINCT user_id) FROM activity_logs
        WHERE activity_type = 'login'
        AND DATE(created_at) = DATE('now')
    ''')
    active_sessions_today = cursor.fetchone()[0]
    
    # Top Active Users (by activity count)
    cursor.execute('''
        SELECT 
            u.username,
            u.full_name,
            COUNT(*) as activity_count,
            MAX(al.created_at) as last_activity
        FROM activity_logs al
        JOIN users u ON al.user_id = u.user_id
        WHERE al.created_at >= datetime('now', '-7 days')
        GROUP BY al.user_id
        ORDER BY activity_count DESC
        LIMIT 10
    ''')
    top_users = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    top_users = [dict(zip(columns, row)) for row in top_users]
    
    # Document Processing Stats
    cursor.execute('''
        SELECT 
            DATE(forwarded_date) as date,
            COUNT(*) as count
        FROM notesheet_movements
        WHERE forwarded_date >= date('now', '-7 days')
        GROUP BY DATE(forwarded_date)
        ORDER BY date DESC
    ''')
    ns_daily_activity = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    ns_daily_activity = [dict(zip(columns, row)) for row in ns_daily_activity]
    
    db.close()
    
    stats = {
        'active_users': active_users,
        'inactive_users': inactive_users,
        'total_notesheets': total_notesheets,
        'total_bills': total_bills,
        'total_ns_movements': total_ns_movements,
        'total_bill_movements': total_bill_movements,
        'failed_logins_24h': failed_logins_24h,
        'active_sessions_today': active_sessions_today
    }
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         activities=activities,
                         top_users=top_users,
                         ns_daily_activity=ns_daily_activity)

@app.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    """View all activity logs with filtering"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get filter parameters
    activity_type = request.args.get('type', '')
    user_id = request.args.get('user', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search = request.args.get('search', '')
    
    # Build query
    query = '''
        SELECT 
            al.log_id,
            al.user_id,
            u.username,
            u.full_name,
            al.activity_type,
            al.description,
            al.ip_address,
            al.session_id,
            al.created_at
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.user_id
        WHERE 1=1
    '''
    params = []
    
    if activity_type:
        query += ' AND al.activity_type = ?'
        params.append(activity_type)
    
    if user_id:
        query += ' AND al.user_id = ?'
        params.append(user_id)
    
    if date_from:
        query += ' AND DATE(al.created_at) >= ?'
        params.append(date_from)
    
    if date_to:
        query += ' AND DATE(al.created_at) <= ?'
        params.append(date_to)
    
    if search:
        query += ' AND (al.description LIKE ? OR u.username LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param])
    
    query += ' ORDER BY al.created_at DESC LIMIT 500'
    
    cursor.execute(query, params)
    logs = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    logs = [dict(zip(columns, row)) for row in logs]
    
    # Get all users for filter dropdown
    cursor.execute('SELECT user_id, username, full_name FROM users ORDER BY username')
    users = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    users = [dict(zip(columns, row)) for row in users]
    
    # Get activity types
    cursor.execute('SELECT DISTINCT activity_type FROM activity_logs ORDER BY activity_type')
    activity_types = [row[0] for row in cursor.fetchall()]
    
    db.close()
    
    return render_template('admin/logs.html',
                         logs=logs,
                         users=users,
                         activity_types=activity_types,
                         filters={
                             'type': activity_type,
                             'user': user_id,
                             'date_from': date_from,
                             'date_to': date_to,
                             'search': search
                         })

# SUPERUSER EDIT ROUTES - INSERT BEFORE "# Error handlers" (line 1133)
    """Edit user - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        section_id = request.form.get('section_id')
        designation = request.form.get('designation')
        new_password = request.form.get('new_password')
        is_active = 1 if request.form.get('is_active') else 0
        is_superuser = 1 if request.form.get('is_superuser') else 0
        roles = request.form.getlist('roles')
        
        # Validation
        if not username or not full_name or not section_id:
            flash('Username, Full Name, and Section are required.', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        if not roles:
            flash('At least one role must be selected.', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        # Check if username already exists (for other users)
        cursor.execute('SELECT user_id FROM users WHERE username = ? AND user_id != ?', (username, user_id))
        if cursor.fetchone():
            flash(f'Username "{username}" is already taken.', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        # Prevent removing own superuser status
        if user_id == current_user.id and not is_superuser:
            flash('You cannot remove your own superuser status.', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
        
        # Update user
        if new_password:
            # Hash the password
            import hashlib
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            cursor.execute('''
                UPDATE users SET
                    username = ?,
                    password_hash = ?,
                    full_name = ?,
                    email = ?,
                    phone = ?,
                    section_id = ?,
                    designation = ?,
                    is_active = ?,
                    is_superuser = ?
                WHERE user_id = ?
            ''', (username, password_hash, full_name, email, phone, section_id, designation, is_active, is_superuser, user_id))
        else:
            cursor.execute('''
                UPDATE users SET
                    username = ?,
                    full_name = ?,
                    email = ?,
                    phone = ?,
                    section_id = ?,
                    designation = ?,
                    is_active = ?,
                    is_superuser = ?
                WHERE user_id = ?
            ''', (username, full_name, email, phone, section_id, designation, is_active, is_superuser, user_id))
        
        # Update roles - delete old mappings and add new ones
        cursor.execute('DELETE FROM user_role_mapping WHERE user_id = ?', (user_id,))
        for role_id in roles:
            cursor.execute('''
                INSERT INTO user_role_mapping (user_id, role_id, assigned_by, assigned_at)
                VALUES (?, ?, ?, datetime('now'))
            ''', (user_id, int(role_id), current_user.id))
        
        conn.commit()
        
        # Log activity
        db.log_activity(
            current_user.id,
            'user_updated',
            f"Updated user: {username} (ID: {user_id})",
            request.remote_addr
        )
        
        db.close()
        flash(f"User '{username}' updated successfully!", 'success')
        return redirect(url_for('admin_users'))
    
    # GET - show form
    cursor.execute('''
        SELECT 
            u.user_id, u.username, u.full_name, u.email, u.phone,
            u.section_id, s.section_name, u.designation, 
            u.is_active, u.is_superuser, u.last_login,
            GROUP_CONCAT(ur.role_name) as roles
        FROM users u
        LEFT JOIN sections s ON u.section_id = s.section_id
        LEFT JOIN user_role_mapping urm ON u.user_id = urm.user_id
        LEFT JOIN user_roles ur ON urm.role_id = ur.role_id
        WHERE u.user_id = ?
        GROUP BY u.user_id
    ''', (user_id,))
    
    user = cursor.fetchone()
    
    if not user:
        db.close()
        flash('User not found.', 'error')
        return redirect(url_for('admin_users'))
    
    columns = [desc[0] for desc in cursor.description]
    user = dict(zip(columns, user))
    
    # Get all sections
    sections = db.get_all_sections()
    
    # Get all roles
    cursor.execute('SELECT * FROM user_roles ORDER BY role_id')
    all_roles = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    all_roles = [dict(zip(columns, row)) for row in all_roles]
    
    db.close()
    
    return render_template('admin/edit_user.html', 
                         user=user, 
                         sections=sections, 
                         all_roles=all_roles)

# SUPERUSER EDIT ROUTES - INSERT BEFORE "# Error handlers" (line 1133)

# Notesheet Edit Routes
@app.route('/notesheets/<int:notesheet_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_notesheet(notesheet_id):
    """Edit notesheet - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Update notesheet
        cursor.execute('''
            UPDATE notesheets SET
                notesheet_number = ?,
                subject = ?,
                sender_name = ?,
                sender_organization = ?,
                sender_address = ?,
                reference_number = ?,
                received_date = ?,
                category = ?,
                priority = ?,
                remarks = ?
            WHERE notesheet_id = ?
        ''', (
            request.form.get('notesheet_number'),
            request.form.get('subject'),
            request.form.get('sender_name'),
            request.form.get('sender_organization'),
            request.form.get('sender_address'),
            request.form.get('reference_number'),
            request.form.get('received_date'),
            request.form.get('category'),
            request.form.get('priority'),
            request.form.get('remarks'),
            notesheet_id
        ))
        conn.commit()
        
        db.log_activity(current_user.id, 'notesheet_edited',
                       f"Edited notesheet ID {notesheet_id}",
                       request.remote_addr)
        
        db.close()
        flash('Notesheet updated successfully!', 'success')
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    # GET - show form
    cursor.execute('SELECT * FROM notesheets WHERE notesheet_id = ?', (notesheet_id,))
    notesheet = cursor.fetchone()
    
    if not notesheet:
        db.close()
        flash('Notesheet not found.', 'error')
        return redirect(url_for('notesheets_list'))
    
    columns = [desc[0] for desc in cursor.description]
    notesheet = dict(zip(columns, notesheet))
    
    db.close()
    return render_template('notesheets/edit.html', notesheet=notesheet)

@app.route('/movements/notesheet/<int:movement_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_notesheet_movement(movement_id):
    """Edit notesheet movement - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        cursor.execute('''
            UPDATE notesheet_movements SET
                forwarded_date = ?,
                comments = ?
            WHERE movement_id = ?
        ''', (
            request.form.get('forwarded_date'),
            request.form.get('comments'),
            movement_id
        ))
        conn.commit()
        
        cursor.execute('SELECT notesheet_id FROM notesheet_movements WHERE movement_id = ?', (movement_id,))
        notesheet_id = cursor.fetchone()[0]
        
        db.log_activity(current_user.id, 'movement_edited',
                       f"Edited notesheet movement ID {movement_id}",
                       request.remote_addr)
        
        db.close()
        flash('Movement updated successfully!', 'success')
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    # GET - show form
    cursor.execute('''
        SELECT nm.*, n.notesheet_number
        FROM notesheet_movements nm
        JOIN notesheets n ON nm.notesheet_id = n.notesheet_id
        WHERE nm.movement_id = ?
    ''', (movement_id,))
    movement = cursor.fetchone()
    
    if not movement:
        db.close()
        flash('Movement not found.', 'error')
        return redirect(url_for('notesheets_list'))
    
    columns = [desc[0] for desc in cursor.description]
    movement = dict(zip(columns, movement))
    
    db.close()
    return render_template('notesheets/edit_movement.html', movement=movement)

@app.route('/movements/notesheet/<int:movement_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_notesheet_movement(movement_id):
    """Delete notesheet movement - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get notesheet_id before deleting
    cursor.execute('SELECT notesheet_id FROM notesheet_movements WHERE movement_id = ?', (movement_id,))
    result = cursor.fetchone()
    
    if not result:
        db.close()
        flash('Movement not found.', 'error')
        return redirect(url_for('notesheets_list'))
    
    notesheet_id = result[0]
    
    # Delete the movement
    cursor.execute('DELETE FROM notesheet_movements WHERE movement_id = ?', (movement_id,))
    conn.commit()
    
    db.log_activity(current_user.id, 'movement_deleted',
                   f"Deleted notesheet movement ID {movement_id}",
                   request.remote_addr)
    
    db.close()
    flash('Movement deleted successfully!', 'success')
    return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))

# Bill Edit Routes
@app.route('/bills/<int:bill_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_bill(bill_id):
    """Edit bill - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Get bill_amount, default to 0 if not provided
        bill_amount_str = request.form.get('bill_amount')
        bill_amount = float(bill_amount_str) if bill_amount_str else 0.0
        
        # Update bill
        cursor.execute('''
            UPDATE bills SET
                bill_number = ?,
                invoice_number = ?,
                vendor_name = ?,
                vendor_address = ?,
                vendor_gstin = ?,
                vendor_pan = ?,
                bill_date = ?,
                received_date = ?,
                bill_amount = ?,
                taxable_amount = ?,
                gst_amount = ?,
                tds_amount = ?,
                net_payable_amount = ?,
                bill_type = ?,
                category = ?,
                priority = ?,
                description = ?,
                remarks = ?
            WHERE bill_id = ?
        ''', (
            request.form.get('bill_number'),
            request.form.get('invoice_number'),
            request.form.get('vendor_name'),
            request.form.get('vendor_address'),
            request.form.get('vendor_gstin'),
            request.form.get('vendor_pan'),
            request.form.get('bill_date'),
            request.form.get('received_date'),
            bill_amount,
            float(request.form.get('taxable_amount') or 0) if request.form.get('taxable_amount') else None,
            float(request.form.get('gst_amount') or 0) if request.form.get('gst_amount') else None,
            float(request.form.get('tds_amount') or 0) if request.form.get('tds_amount') else None,
            float(request.form.get('net_payable_amount') or 0) if request.form.get('net_payable_amount') else None,
            request.form.get('bill_type'),
            request.form.get('category'),
            request.form.get('priority'),
            request.form.get('description'),
            request.form.get('remarks'),
            bill_id
        ))
        conn.commit()
        
        db.log_activity(current_user.id, 'bill_edited',
                       f"Edited bill ID {bill_id}",
                       request.remote_addr)
        
        db.close()
        flash('Bill updated successfully!', 'success')
        return redirect(url_for('bill_detail', bill_id=bill_id))
    
    # GET - show form
    cursor.execute('SELECT * FROM bills WHERE bill_id = ?', (bill_id,))
    bill = cursor.fetchone()
    
    if not bill:
        db.close()
        flash('Bill not found.', 'error')
        return redirect(url_for('bills_list'))
    
    columns = [desc[0] for desc in cursor.description]
    bill = dict(zip(columns, bill))
    
    db.close()
    return render_template('bills/edit.html', bill=bill)

@app.route('/movements/bill/<int:movement_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_bill_movement(movement_id):
    """Edit bill movement - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        cursor.execute('''
            UPDATE bill_movements SET
                forwarded_date = ?,
                comments = ?
            WHERE movement_id = ?
        ''', (
            request.form.get('forwarded_date'),
            request.form.get('comments'),
            movement_id
        ))
        conn.commit()
        
        cursor.execute('SELECT bill_id FROM bill_movements WHERE movement_id = ?', (movement_id,))
        bill_id = cursor.fetchone()[0]
        
        db.log_activity(current_user.id, 'movement_edited',
                       f"Edited bill movement ID {movement_id}",
                       request.remote_addr)
        
        db.close()
        flash('Movement updated successfully!', 'success')
        return redirect(url_for('bill_detail', bill_id=bill_id))
    
    # GET - show form
    cursor.execute('''
        SELECT bm.*, b.bill_number
        FROM bill_movements bm
        JOIN bills b ON bm.bill_id = b.bill_id
        WHERE bm.movement_id = ?
    ''', (movement_id,))
    movement = cursor.fetchone()
    
    if not movement:
        db.close()
        flash('Movement not found.', 'error')
        return redirect(url_for('bills_list'))
    
    columns = [desc[0] for desc in cursor.description]
    movement = dict(zip(columns, movement))
    
    db.close()
    return render_template('bills/edit_movement.html', movement=movement)

@app.route('/movements/bill/<int:movement_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_bill_movement(movement_id):
    """Delete bill movement - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get bill_id before deleting
    cursor.execute('SELECT bill_id FROM bill_movements WHERE movement_id = ?', (movement_id,))
    result = cursor.fetchone()
    
    if not result:
        db.close()
        flash('Movement not found.', 'error')
        return redirect(url_for('bills_list'))
    
    bill_id = result[0]
    
    # Delete the movement
    cursor.execute('DELETE FROM bill_movements WHERE movement_id = ?', (movement_id,))
    conn.commit()
    
    db.log_activity(current_user.id, 'movement_deleted',
                   f"Deleted bill movement ID {movement_id}",
                   request.remote_addr)
    
    db.close()
    flash('Movement deleted successfully!', 'success')
    return redirect(url_for('bill_detail', bill_id=bill_id))


# =============================================================================
# DELETE ROUTES FOR DOCUMENTS (Notesheets, Bills, Letters)
# =============================================================================

# Delete Notesheet
@app.route('/notesheets/<int:notesheet_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_notesheet(notesheet_id):
    """Delete notesheet - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    try:
        # Get notesheet info before deleting
        cursor.execute('SELECT notesheet_number FROM notesheets WHERE notesheet_id = ?', (notesheet_id,))
        result = cursor.fetchone()
        
        if not result:
            flash('Notesheet not found.', 'error')
            db.close()
            return redirect(url_for('notesheets_list'))
        
        notesheet_number = result[0]
        
        # Delete movements first (foreign key)
        cursor.execute('DELETE FROM notesheet_movements WHERE notesheet_id = ?', (notesheet_id,))
        
        # Delete notesheet
        cursor.execute('DELETE FROM notesheets WHERE notesheet_id = ?', (notesheet_id,))
        
        conn.commit()
        
        # Log activity
        db.log_activity(
            current_user.id,
            'notesheet_deleted',
            f"Deleted notesheet: {notesheet_number} (ID: {notesheet_id})",
            request.remote_addr
        )
        
        flash(f'Notesheet "{notesheet_number}" deleted successfully!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting notesheet: {str(e)}', 'error')
    
    db.close()
    return redirect(url_for('notesheets_list'))

# Delete Bill
@app.route('/bills/<int:bill_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_bill(bill_id):
    """Delete bill - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    try:
        # Get bill info before deleting
        cursor.execute('SELECT bill_number FROM bills WHERE bill_id = ?', (bill_id,))
        result = cursor.fetchone()
        
        if not result:
            flash('Bill not found.', 'error')
            db.close()
            return redirect(url_for('bills_list'))
        
        bill_number = result[0]
        
        # Delete movements first (foreign key)
        cursor.execute('DELETE FROM bill_movements WHERE bill_id = ?', (bill_id,))
        
        # Delete bill
        cursor.execute('DELETE FROM bills WHERE bill_id = ?', (bill_id,))
        
        conn.commit()
        
        # Log activity
        db.log_activity(
            current_user.id,
            'bill_deleted',
            f"Deleted bill: {bill_number} (ID: {bill_id})",
            request.remote_addr
        )
        
        flash(f'Bill "{bill_number}" deleted successfully!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting bill: {str(e)}', 'error')
    
    db.close()
    return redirect(url_for('bills_list'))

# Delete Letter
@app.route('/letters/<int:letter_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_letter(letter_id):
    """Delete letter - superuser only"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    
    try:
        # Get letter info before deleting
        cursor.execute('SELECT letter_number FROM letters WHERE letter_id = ?', (letter_id,))
        result = cursor.fetchone()
        
        if not result:
            flash('Letter not found.', 'error')
            db.close()
            return redirect(url_for('letters_list'))
        
        letter_number = result[0]
        
        # Delete movements first (foreign key)
        cursor.execute('DELETE FROM letter_movements WHERE letter_id = ?', (letter_id,))
        
        # Delete letter
        cursor.execute('DELETE FROM letters WHERE letter_id = ?', (letter_id,))
        
        conn.commit()
        
        # Log activity
        db.log_activity(
            current_user.id,
            'letter_deleted',
            f"Deleted letter: {letter_number} (ID: {letter_id})",
            request.remote_addr
        )
        
        flash(f'Letter "{letter_number}" deleted successfully!', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting letter: {str(e)}', 'error')
    
    db.close()
    return redirect(url_for('letters_list'))




# Error handlers

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('errors/500.html'), 500

# Run the application
if __name__ == '__main__':
    print("=" * 60)
    print("WBSEDCL Tracking System Starting...")
    print("=" * 60)
    print("Access the application at: http://127.0.0.1:5000")
    print("Default login: admin / admin123")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
    print("Access the application at: http://127.0.0.1:5000")
    print("Default login: admin / admin123")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)