# WBSEDCL Document Tracking System

A comprehensive web-based document tracking system for managing notesheets and bills with role-based access control, section-wise workflow management, real-time document movement tracking, and advanced admin monitoring.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![SQLite](https://img.shields.io/badge/SQLite-3-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [User Roles & Permissions](#user-roles--permissions)
- [Forwarding Rules](#forwarding-rules)
- [Usage Guide](#usage-guide)
- [Admin Features](#admin-features)
- [Security Features](#security-features)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## ✨ Features

### Core Features
- **Document Management**
  - Notesheet tracking with full lifecycle management
  - Bill tracking with payment status monitoring
  - Document parking for pending items
  - Custom forward dates for backdated entries
  - Complete movement history with time tracking

- **Role-Based Access Control**
  - Superuser: Full system access and user management
  - Receive Section: Document intake and routing to any section
  - Section Head: Forward within section and to other heads
  - Section Member: Forward only to section head
  - Viewer: Read-only access

- **Movement Tracking**
  - Complete audit trail with IN/OUT dates
  - Time-held calculation (days at each location)
  - Section-wise routing with user identification
  - Real-time status updates
  - Section head names displayed in movement history

- **Advanced Features**
  - Cascading dropdowns for section → user selection
  - Personalized dashboard showing user's documents
  - Activity logging with session tracking
  - Search and filter capabilities
  - Priority-based document handling
  - User profile management
  - Failed login attempt tracking

### Admin Monitoring Features
- **Admin Dashboard**
  - System statistics (active users, sessions, documents)
  - Failed login monitoring (24-hour tracking)
  - Top active users (7-day analysis)
  - Daily activity charts
  - Real-time activity feed

- **Activity Logs**
  - Advanced filtering (type, user, date range)
  - Session-based activity grouping
  - Export to CSV functionality
  - Comprehensive audit trail
  - IP address tracking

- **Security Monitoring**
  - Failed login attempt logging (with attempted username)
  - Session tracking (unique session IDs)
  - User activity timeline
  - Suspicious pattern detection
  - System user tracking for unknown login attempts

### UI/UX Features
- Responsive Bootstrap 5 interface
- Beautiful movement history with badges and icons
- Clickable dashboard cards
- Section head names in movement history
- Permission-based button visibility
- Hover effects and transitions
- Color-coded activity badges
- Empty state messages based on permissions

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Flask Web Application                    │
├─────────────────────────────────────────────────────────────┤
│  Authentication Layer (Flask-Login)                          │
│  ├── User Management                                         │
│  ├── Session Management (UUID-based)                         │
│  └── Permission Checking                                     │
├─────────────────────────────────────────────────────────────┤
│  Business Logic Layer                                        │
│  ├── Notesheet Management                                    │
│  ├── Bill Management                                         │
│  ├── Forwarding Rules Engine                                │
│  ├── Activity Logging with Sessions                         │
│  └── Failed Login Tracking                                  │
├─────────────────────────────────────────────────────────────┤
│  Data Access Layer (WBSEDCLDatabase)                        │
│  ├── SQLite Connection Pool                                  │
│  ├── Query Optimization                                      │
│  └── Transaction Management                                  │
├─────────────────────────────────────────────────────────────┤
│  Database (SQLite)                                           │
│  ├── users, user_roles, user_role_mapping                   │
│  ├── sections, sub_sections                                 │
│  ├── notesheets, notesheet_movements                        │
│  ├── bills, bill_movements                                   │
│  └── activity_logs (with session_id tracking)              │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Web browser (Chrome, Firefox, Edge, Safari)
- Windows/Linux/macOS

## 🚀 Installation

### Step 1: Clone or Download the Project

```bash
cd C:\Development\receive\receive_section
```

### Step 2: Create Virtual Environment

```powershell
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```powershell
pip install flask flask-login
```

### Step 4: Initialize Database

```powershell
python init_database.py
```

This creates:
- SQLite database file: `wbsedcl_tracking.db`
- All required tables with relationships
- Default sections and roles
- Default admin user
- System user (ID=0) for failed login tracking

### Step 5: Add Required Columns

```powershell
# Add section head permission column
python add_is_section_head_column.py

# Add system user for failed login tracking
python add_system_user.py

# Add session tracking (optional but recommended)
python add_session_tracking.py
```

### Step 6: Run the Application

```powershell
python app.py
```

The application will start on: `http://127.0.0.1:5000`

### Step 7: First Login

```
Username: admin
Password: admin123
```

**Important:** Change the admin password immediately after first login via Profile page!

## 🗄️ Database Setup

### Automatic Setup
Running `init_database.py` creates the complete database structure:

```
wbsedcl_tracking.db
├── users                    # User accounts
├── user_roles              # Role definitions with permissions
├── user_role_mapping       # User-to-role assignments
├── sections                # Organizational sections
├── sub_sections            # Sub-sections (optional)
├── notesheets              # Notesheet master table
├── notesheet_movements     # Notesheet routing history
├── bills                   # Bill master table
├── bill_movements          # Bill routing history
├── notesheet_attachments   # File attachments (future)
├── bill_attachments        # File attachments (future)
└── activity_logs           # Audit trail with session tracking
```

### Default Data Created

**Sections:**
1. Receive Section (ID: 1)
2. Divisional Manager (ID: 2)
3. HR Section (ID: 3)
4. DCC Section (ID: 4)
5. Accounts Section (ID: 5)

**User Roles:**
1. Superuser - Full access
2. Receive Section - Can receive & forward to anyone
3. Section Head - Can forward within section & to other heads
4. Section Member - Can forward to section head only
5. Viewer - Read-only access

**Default Users:**
```
Admin (Superuser):
  Username: admin
  Password: admin123
  Section: Receive Section

System User (ID: 0):
  Username: system
  Purpose: Track failed logins with unknown usernames
```

## 👥 User Roles & Permissions

### Superuser
**Access Level:** Complete system control

**Permissions:**
- ✅ Create, edit, delete users
- ✅ Assign/remove roles
- ✅ Change user sections
- ✅ Edit notesheet/bill details
- ✅ Modify movement history
- ✅ View all documents
- ✅ Access admin dashboard
- ✅ View activity logs
- ✅ Change own username and section

**Use Cases:**
- System administration
- User management
- Data correction
- Security monitoring

### Receive Section
**Access Level:** Document intake and routing

**Permissions:**
- ✅ Receive new notesheets/bills
- ✅ Forward to ANY section
- ✅ Park documents
- ✅ View parked items
- ✅ Search all documents

**Use Cases:**
- Initial document receipt
- Document registration
- Routing to appropriate sections
- Managing parked documents

### Section Head
**Access Level:** Section management

**Permissions:**
- ✅ Forward to users in own section
- ✅ Forward to other section heads
- ✅ Forward to receive section
- ✅ View section documents
- ❌ Cannot receive new documents
- ❌ Cannot change username or section

**Use Cases:**
- Managing section workflow
- Distributing work within section
- Coordinating with other sections

### Section Member
**Access Level:** Basic document handling

**Permissions:**
- ✅ Forward to section head only
- ✅ View assigned documents
- ✅ Update profile (email, phone, designation)
- ❌ Cannot receive documents
- ❌ Cannot forward outside section
- ❌ Cannot change username or section

**Use Cases:**
- Processing assigned documents
- Reporting to section head
- Basic document handling

### Viewer
**Access Level:** Read-only monitoring

**Permissions:**
- ✅ View document status
- ✅ Search documents
- ❌ Cannot forward
- ❌ Cannot receive
- ❌ Cannot edit

**Use Cases:**
- Management oversight
- Status monitoring
- Report generation

## 🔀 Forwarding Rules

### Rule Matrix

| Current User Role | Can Forward To |
|------------------|----------------|
| **Superuser** | Everyone |
| **Receive Section** | Everyone |
| **Section Head** | • Own section members<br>• Other section heads<br>• Receive section |
| **Section Member** | Section head only |
| **Viewer** | Nobody |

### Exclusions
- Current holder is excluded from recipient list
- Inactive users are excluded
- Superusers are excluded (they don't process documents)

## 📖 Usage Guide

### For All Users

#### Accessing Profile
1. Click your name in top-right corner
2. Select **Profile**
3. Update your information:
   - Full Name
   - Email
   - Phone
   - Designation
   - Change Password (requires current password)
4. Click **Save Changes**

**Note:** 
- Username and Section are read-only (except for superusers)
- Password change requires current password verification

#### Viewing Your Documents
1. Click **Dashboard**
2. Click **My Notesheets** or **My Bills** card
3. All documents currently assigned to you are displayed

### For Receive Section Users

#### Receiving a Notesheet
1. Click **Receive** → **Receive Notesheet**
2. Fill in required fields:
   - Notesheet Number (unique)
   - Subject
   - Sender Name
   - Received Date
   - Priority (Normal/High/Urgent)
3. Click **Receive Notesheet**
4. System creates initial movement record

#### Forwarding to a Section
1. Go to **Notesheets** → Click notesheet
2. In **Forward Document** panel:
   - Select Section from dropdown
   - Select User (filtered by section)
   - Choose Action (Forward/Review/Approve)
   - Set Forward Date
   - Add Comments (optional)
3. Click **Forward**

### For Section Heads

#### Distributing Work
1. Open document detail page
2. **Forward Document** panel shows:
   - Your section members
   - Other section heads
   - Receive section
3. Select appropriate user and forward

### For Admins (Superuser)

#### Creating a New User
1. Go to **Admin** → **User Management**
2. Click **Create User**
3. Fill in details:
   - Username (unique)
   - Password
   - Full Name
   - Email (optional)
   - Section (required)
   - Designation
   - Roles (select at least one)
4. Click **Create User**

#### Editing a User
1. Go to **User Management**
2. Click **Edit** (pencil icon) on user row
3. Modify:
   - Username
   - Full name
   - Section assignment
   - Roles
   - Password (optional)
   - Active/Inactive status
   - Superuser status
4. Click **Save Changes**

#### Viewing Activity Logs
1. Go to **Admin** → **Activity Logs**
2. Use filters:
   - Activity Type
   - User
   - Date Range
   - Search Description
3. View session-grouped activities
4. Export to CSV if needed

## 🔐 Security Features

### Failed Login Tracking
- **Existing User, Wrong Password:**
  ```
  User: admin
  Activity: Login Failed
  Description: Failed login: Invalid password. Username attempted: admin
  ```

- **Non-existent Username:**
  ```
  User: System
  Activity: Login Failed
  Description: Failed login: Invalid username and password. Username attempted: hacker123
  ```

### Session Tracking
- Unique UUID generated per login session
- All activities grouped by session_id
- Complete user session timeline from login to logout
- Session-based forensics capability

### Activity Logging
All user actions are logged with:
- User ID and username
- Activity type (color-coded)
- Description
- IP address
- Session ID
- Timestamp

### Password Security
- SHA256 hashing
- Current password verification for changes
- Password confirmation required
- No plain-text storage

## 📁 Project Structure

```
receive_section/
├── app.py                          # Main Flask application
├── init_database.py                # Database initialization script
├── add_is_section_head_column.py  # Permission fix script
├── add_system_user.py             # System user for failed logins
├── add_session_tracking.py        # Add session tracking column
├── wbsedcl_tracking.db            # SQLite database (created on init)
├── requirements.txt               # Python dependencies
├── README.md                      # This file
│
├── templates/                     # HTML templates
│   ├── base.html                 # Base template with navigation
│   ├── login.html                # Login page
│   ├── dashboard.html            # User dashboard
│   ├── user_profile.html         # User profile page
│   │
│   ├── notesheets/               # Notesheet templates
│   │   ├── list.html            # Notesheet list with filters
│   │   ├── detail.html          # Notesheet detail with movements
│   │   ├── receive.html         # Receive notesheet form
│   │   ├── edit.html            # Edit notesheet (superuser)
│   │   └── edit_movement.html   # Edit movement (superuser)
│   │
│   ├── bills/                    # Bill templates
│   │   ├── list.html            # Bill list with filters
│   │   ├── detail.html          # Bill detail with movements
│   │   ├── receive.html         # Receive bill form
│   │   ├── edit.html            # Edit bill (superuser)
│   │   └── edit_movement.html   # Edit movement (superuser)
│   │
│   ├── admin/                    # Admin templates
│   │   ├── dashboard.html       # Admin monitoring dashboard
│   │   ├── logs.html            # Activity logs with filtering
│   │   ├── users.html           # User management
│   │   └── edit_user.html       # Edit user form
│   │
│   └── errors/                   # Error pages
│       ├── 404.html             # Page not found
│       └── 500.html             # Server error
│
└── static/                       # Static assets
    ├── css/
    │   └── style.css            # Custom styles
    └── js/
        └── main.js              # JavaScript functionality
```

## ⚙️ Configuration

### Security Recommendations

1. **Change Secret Key:**
   ```python
   import secrets
   secret_key = secrets.token_hex(32)
   # Use this in app.config['SECRET_KEY']
   ```

2. **Change Default Passwords:**
   - Login as admin
   - Go to Profile
   - Change password immediately

3. **Production Deployment:**
   ```python
   # Disable debug mode
   app.run(debug=False)
   ```

4. **Database Backups:**
   ```powershell
   # Regular backups
   copy wbsedcl_tracking.db backups\wbsedcl_$(Get-Date -Format 'yyyyMMdd_HHmmss').db
   ```

## 🔧 Troubleshooting

### Common Issues

#### Issue: "No module named flask"
**Solution:**
```powershell
# Ensure virtual environment is activated
.\venv\Scripts\activate

# Install dependencies
pip install flask flask-login
```

#### Issue: "Permission denied" on forwarding
**Solution:**
```powershell
# Run the permission fix script
python add_is_section_head_column.py

# Restart Flask
python app.py
```

#### Issue: Failed logins not showing in logs
**Solution:**
```powershell
# Add system user for failed login tracking
python add_system_user.py

# Restart Flask
python app.py
```

#### Issue: Empty dropdown when forwarding
**Solution:**
1. Check if user is current holder
2. Verify SQL query returns users (check PowerShell console for DEBUG output)
3. Check browser console (F12) for JavaScript errors

#### Issue: Profile page shows 404
**Solution:**
```powershell
# Ensure templates are deployed
copy user_profile.html templates\user_profile.html

# Restart Flask
python app.py
```

### Debug Mode

Check PowerShell console output when loading pages:
```
DEBUG NOTESHEET: User ID=4, Section ID=4
DEBUG NOTESHEET: Query returned 5 users
```

### Database Inspection

```powershell
# Open database
sqlite3 wbsedcl_tracking.db

# Check user roles
SELECT u.username, ur.role_name 
FROM users u 
JOIN user_role_mapping urm ON u.user_id = urm.user_id
JOIN user_roles ur ON urm.role_id = ur.role_id;

# Check failed logins
SELECT * FROM activity_logs WHERE activity_type = 'login_failed' ORDER BY created_at DESC LIMIT 10;

# Check sessions
SELECT DISTINCT session_id, COUNT(*) as activity_count 
FROM activity_logs 
WHERE session_id IS NOT NULL 
GROUP BY session_id 
ORDER BY created_at DESC;
```

## 📄 License

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2026 WBSEDCL

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR DEALINGS IN THE
SOFTWARE.
```

## 🎯 Roadmap

### Planned Features

- [ ] Email notifications on document forwarding
- [ ] PDF export of movement history
- [ ] Advanced search with date ranges
- [ ] Document attachments (file upload)
- [ ] Reports and analytics dashboard
- [ ] Mobile app (iOS/Android)
- [ ] Barcode/QR code for documents
- [ ] SMS notifications
- [ ] Integration with existing systems
- [ ] Multi-language support
- [ ] Dark mode UI
- [ ] Two-factor authentication
- [ ] LDAP/Active Directory integration

### Version History

**v1.2.0** (2026-01-12)
- ✅ Session tracking for activity monitoring
- ✅ Failed login attempt logging (all usernames)
- ✅ User profile page with permission-based editing
- ✅ Admin dashboard with system monitoring
- ✅ Activity logs with advanced filtering
- ✅ Export logs to CSV
- ✅ System user for unknown login attempts

**v1.1.0** (2026-01-11)
- ✅ Section head forwarding fix
- ✅ User edit functionality for admins
- ✅ Movement history with section head names
- ✅ Personalized dashboard

**v1.0.0** (2026-01-10)
- ✅ Initial release
- ✅ Basic notesheet and bill tracking
- ✅ Role-based access control
- ✅ Section-wise workflow
- ✅ Movement history with time tracking
- ✅ User management

---

**Built with ❤️ for WBSEDCL**

*Last Updated: January 12, 2026*

## 📞 Support

For issues, questions, or suggestions:

1. Check this README first
2. Review [Troubleshooting](#troubleshooting) section
3. Check application logs (PowerShell console)
4. Create an issue with:
   - Description of problem
   - Steps to reproduce
   - Error messages
   - Screenshots (if applicable)

## 🙏 Acknowledgments

- Flask framework for Python web development
- Bootstrap 5 for responsive UI
- Bootstrap Icons for beautiful iconography
- SQLite for reliable data storage
- Flask-Login for authentication management

---

**System Status:** Production Ready ✅  
**Current Version:** 1.2.0  
**Last Updated:** January 12, 2026