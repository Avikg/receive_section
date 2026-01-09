"""
WBSEDCL Tracking System - Main Application
Flask web application for notesheet and bill tracking
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
    def __init__(self, user_id, username, full_name, email,
                 department, designation, is_active, is_superuser):
        self.id = user_id
        self.username = username
        self.full_name = full_name
        self.email = email
        self.department = department
        self.designation = designation

        # IMPORTANT: internal flag (do NOT overwrite UserMixin property)
        self._is_active = bool(is_active)

        self.is_superuser = bool(is_superuser)
        self._permissions = None

    # Flask-Login expects this property
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

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    db = WBSEDCLDatabase()
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, full_name, email, department, designation, is_active, is_superuser
        FROM users WHERE user_id = ?
    ''', (user_id,))
    user_data = cursor.fetchone()
    db.close()
    
    if user_data and user_data[6]:  # Check is_active
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
                user_data['department'],
                user_data['designation'],
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
    
    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM notesheets')
    total_notesheets = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM notesheets WHERE current_status != 'Closed'")
    pending_notesheets = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM bills')
    total_bills = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bills WHERE payment_status = 'Pending'")
    pending_bills = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM (
            SELECT notesheet_id FROM notesheets WHERE current_holder = ?
            UNION
            SELECT bill_id FROM bills WHERE current_holder = ?
        )
    ''', (current_user.id, current_user.id))
    my_pending_items = cursor.fetchone()[0]
    
    db.close()
    
    stats = {
        'total_notesheets': total_notesheets,
        'pending_notesheets': pending_notesheets,
        'total_bills': total_bills,
        'pending_bills': pending_bills,
        'my_pending_items': my_pending_items
    }
    
    return render_template('dashboard.html', stats=stats)

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
    
    # Build query
    query = '''
        SELECT 
            n.notesheet_id, n.notesheet_number, n.subject, n.sender_name,
            n.received_date, n.current_status, n.priority,
            u.full_name as current_holder_name
        FROM notesheets n
        LEFT JOIN users u ON n.current_holder = u.user_id
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
    
    # Get notesheet details
    cursor.execute('''
        SELECT 
            n.*,
            u1.full_name as current_holder_name,
            u2.full_name as received_by_name
        FROM notesheets n
        LEFT JOIN users u1 ON n.current_holder = u1.user_id
        LEFT JOIN users u2 ON n.received_by = u2.user_id
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
    
    # Get movement history
    cursor.execute('''
        SELECT 
            nm.*,
            u1.full_name as from_user_name,
            u2.full_name as to_user_name,
            u3.full_name as forwarded_by_name
        FROM notesheet_movements nm
        LEFT JOIN users u1 ON nm.from_user = u1.user_id
        LEFT JOIN users u2 ON nm.to_user = u2.user_id
        LEFT JOIN users u3 ON nm.forwarded_by = u3.user_id
        WHERE nm.notesheet_id = ?
        ORDER BY nm.forwarded_date DESC
    ''', (notesheet_id,))
    
    movements = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    movements = [dict(zip(columns, row)) for row in movements]
    
    # Get all users for forwarding
    cursor.execute('SELECT user_id, full_name, designation, department FROM users WHERE is_active = 1 AND user_id != ?', (current_user.id,))
    users = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    users = [dict(zip(columns, row)) for row in users]
    
    db.close()
    
    return render_template('notesheets/detail.html', notesheet=notesheet, movements=movements, users=users)

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
            'received_by': current_user.id
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
    
    if not to_user:
        flash('Please select a user to forward to.', 'error')
        return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))
    
    db = WBSEDCLDatabase()
    
    movement_data = {
        'notesheet_id': notesheet_id,
        'from_user': current_user.id,
        'to_user': int(to_user),
        'forwarded_by': current_user.id,
        'action_taken': action,
        'comments': comments
    }
    
    success = db.forward_notesheet(movement_data)
    
    if success:
        db.log_activity(current_user.id, 'notesheet_forwarded',
                       f"Forwarded notesheet ID {notesheet_id} to user ID {to_user}",
                       request.remote_addr)
        flash('Notesheet forwarded successfully!', 'success')
    else:
        flash('Failed to forward notesheet.', 'error')
    
    db.close()
    return redirect(url_for('notesheet_detail', notesheet_id=notesheet_id))

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
    
    # Build query
    query = '''
        SELECT 
            b.bill_id, b.bill_number, b.invoice_number, b.vendor_name,
            b.bill_amount, b.received_date, b.current_status, b.payment_status, b.priority,
            u.full_name as current_holder_name
        FROM bills b
        LEFT JOIN users u ON b.current_holder = u.user_id
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
    
    # Get bill details
    cursor.execute('''
        SELECT 
            b.*,
            u1.full_name as current_holder_name,
            u2.full_name as received_by_name
        FROM bills b
        LEFT JOIN users u1 ON b.current_holder = u1.user_id
        LEFT JOIN users u2 ON b.received_by = u2.user_id
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
    
    # Get movement history
    cursor.execute('''
        SELECT 
            bm.*,
            u1.full_name as from_user_name,
            u2.full_name as to_user_name,
            u3.full_name as forwarded_by_name
        FROM bill_movements bm
        LEFT JOIN users u1 ON bm.from_user = u1.user_id
        LEFT JOIN users u2 ON bm.to_user = u2.user_id
        LEFT JOIN users u3 ON bm.forwarded_by = u3.user_id
        WHERE bm.bill_id = ?
        ORDER BY bm.forwarded_date DESC
    ''', (bill_id,))
    
    movements = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    movements = [dict(zip(columns, row)) for row in movements]
    
    # Get all users for forwarding
    cursor.execute('SELECT user_id, full_name, designation, department FROM users WHERE is_active = 1 AND user_id != ?', (current_user.id,))
    users = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    users = [dict(zip(columns, row)) for row in users]
    
    db.close()
    
    return render_template('bills/detail.html', bill=bill, movements=movements, users=users)

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
            'bill_amount': float(request.form.get('bill_amount', 0)),
            'taxable_amount': float(request.form.get('taxable_amount') or 0) if request.form.get('taxable_amount') else None,
            'gst_amount': float(request.form.get('gst_amount') or 0) if request.form.get('gst_amount') else None,
            'tds_amount': float(request.form.get('tds_amount') or 0) if request.form.get('tds_amount') else None,
            'net_payable_amount': float(request.form.get('net_payable_amount') or 0) if request.form.get('net_payable_amount') else None,
            'bill_type': request.form.get('bill_type'),
            'category': request.form.get('category'),
            'priority': request.form.get('priority', 'Normal'),
            'description': request.form.get('description'),
            'remarks': request.form.get('remarks'),
            'received_by': current_user.id
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
    
    if not to_user:
        flash('Please select a user to forward to.', 'error')
        return redirect(url_for('bill_detail', bill_id=bill_id))
    
    db = WBSEDCLDatabase()
    
    movement_data = {
        'bill_id': bill_id,
        'from_user': current_user.id,
        'to_user': int(to_user),
        'forwarded_by': current_user.id,
        'action_taken': action,
        'comments': comments
    }
    
    success = db.forward_bill(movement_data)
    
    if success:
        db.log_activity(current_user.id, 'bill_forwarded',
                       f"Forwarded bill ID {bill_id} to user ID {to_user}",
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
    
    # Get all users with their roles
    cursor.execute('''
        SELECT 
            u.user_id, u.username, u.full_name, u.email, u.department, 
            u.designation, u.is_active, u.is_superuser, u.last_login,
            GROUP_CONCAT(ur.role_name) as roles
        FROM users u
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
    
    db.close()
    
    return render_template('admin/users.html', users=users, roles=roles)

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
        
        # Create the user
        user_id = db.create_user(
            username=data['username'],
            password=data['password'],
            full_name=data['full_name'],
            email=data.get('email'),
            department=data.get('department'),
            designation=data.get('designation'),
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
        
        # Get user details with roles
        cursor.execute('''
            SELECT 
                u.user_id, u.username, u.full_name, u.email, u.department, 
                u.designation, u.is_active, u.is_superuser, u.last_login,
                GROUP_CONCAT(ur.role_name) as roles
            FROM users u
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
                'department': user[4],
                'designation': user[5],
                'is_active': user[6],
                'is_superuser': user[7],
                'last_login': user[8],
                'roles': user[9].split(',') if user[9] else []
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