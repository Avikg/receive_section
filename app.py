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
    """Quick version check - DO NOT DELETE"""
    return "VERSION: 2026-01-11-FIXED-FORWARDING-v4 | Lines: 1629"

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
            # Update last login
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_login = ? WHERE user_id = ?', 
                         (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_data['user_id']))
            conn.commit()
            
            # Log activity
            db.log_activity(user_data['user_id'], 'login', 'User logged in', request.remote_addr)
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
            db.close()
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    db = WBSEDCLDatabase()
    db.log_activity(current_user.id, 'logout', 'User logged out', request.remote_addr)
    db.close()
    
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

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
    
    # Total items with me (for "My Pending Items" card)
    my_pending_items = my_pending_notesheets + my_pending_bills
    
    # Get parked documents count (Receive Section only)
    parked_count = 0
    if current_user.is_receive_section():
        cursor.execute('SELECT COUNT(*) FROM notesheets WHERE is_parked = 1')
        parked_ns = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM bills WHERE is_parked = 1')
        parked_bills = cursor.fetchone()[0]
        parked_count = parked_ns + parked_bills
    
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
    
    db.close()
    
    stats = {
        'total_notesheets': my_notesheets,
        'pending_notesheets': my_pending_notesheets,
        'total_bills': my_bills,
        'pending_bills': my_pending_bills,
        'my_pending_items': my_pending_items,
        'parked_items': parked_count
    }
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_notesheets=recent_notesheets,
                         recent_bills=recent_bills)

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
@forward_permission_required
def forward_notesheet_route(notesheet_id):
    """Forward a notesheet to another user"""
    to_user = request.form.get('to_user')
    action = request.form.get('action', 'Forwarded')
    comments = request.form.get('comments')
    forward_date = request.form.get('forward_date')  # Get the custom forward date
    
    if not to_user:
        flash('Please select a user to forward to.', 'error')
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    if not forward_date:
        flash('Please provide forward date.', 'error')
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    db = WBSEDCLDatabase()
    
    movement_data = {
        'notesheet_id': notesheet_id,
        'from_user': current_user.id,
        'to_user': int(to_user),
        'forwarded_by': current_user.id,
        'action_taken': action,
        'comments': comments,
        'forward_date': forward_date  # Pass custom date
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
@forward_permission_required
def forward_bill_route(bill_id):
    """Forward a bill to another user"""
    to_user = request.form.get('to_user')
    action = request.form.get('action', 'Forwarded')
    comments = request.form.get('comments')
    forward_date = request.form.get('forward_date')  # Get the custom forward date
    
    if not to_user:
        flash('Please select a user to forward to.', 'error')
        return redirect(url_for('bill_detail', bill_id=bill_id))
    
    if not forward_date:
        flash('Please provide forward date.', 'error')
        return redirect(url_for('bill_detail', bill_id=bill_id))
    
    db = WBSEDCLDatabase()
    
    movement_data = {
        'bill_id': bill_id,
        'from_user': current_user.id,
        'to_user': int(to_user),
        'forwarded_by': current_user.id,
        'action_taken': action,
        'comments': comments,
        'forward_date': forward_date  # Pass custom date
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