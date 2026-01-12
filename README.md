# WBSEDCL Document Tracking System

A comprehensive web-based document tracking system for managing notesheets and bills with role-based access control, section-wise workflow management, and real-time document movement tracking.

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

- **Advanced Features**
  - Cascading dropdowns for section → user selection
  - Personalized dashboard showing user's documents
  - Activity logging for all actions
  - Search and filter capabilities
  - Priority-based document handling

### UI/UX Features
- Responsive Bootstrap 5 interface
- Beautiful movement history with badges and icons
- Clickable dashboard cards
- Section head names in movement history
- Permission-based button visibility
- Hover effects and transitions

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Flask Web Application                    │
├─────────────────────────────────────────────────────────────┤
│  Authentication Layer (Flask-Login)                          │
│  ├── User Management                                         │
│  ├── Session Management                                      │
│  └── Permission Checking                                     │
├─────────────────────────────────────────────────────────────┤
│  Business Logic Layer                                        │
│  ├── Notesheet Management                                    │
│  ├── Bill Management                                         │
│  ├── Forwarding Rules Engine                                │
│  └── Activity Logging                                        │
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
│  └── activity_logs                                           │
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

### Step 5: Add Section Head Permission

```powershell
python add_is_section_head_column.py
```

This adds the `is_section_head` column to the `user_roles` table.

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

**Important:** Change the admin password immediately after first login!

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
└── activity_logs           # Audit trail
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
- ✅ Access admin panel

### Receive Section
**Access Level:** Document intake and routing

**Permissions:**
- ✅ Receive new notesheets/bills
- ✅ Forward to ANY section
- ✅ Park documents
- ✅ View parked items
- ✅ Search all documents

### Section Head
**Access Level:** Section management

**Permissions:**
- ✅ Forward to users in own section
- ✅ Forward to other section heads
- ✅ Forward to receive section
- ✅ View section documents
- ❌ Cannot receive new documents

### Section Member
**Access Level:** Basic document handling

**Permissions:**
- ✅ Forward to section head only
- ✅ View assigned documents
- ❌ Cannot receive documents
- ❌ Cannot forward outside section

### Viewer
**Access Level:** Read-only monitoring

**Permissions:**
- ✅ View document status
- ✅ Search documents
- ❌ Cannot forward
- ❌ Cannot receive
- ❌ Cannot edit

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

### For Receive Section Users

#### Receiving a Notesheet
1. Click **Dashboard** → **Receive Notesheet**
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

#### Viewing Your Documents
1. Click **Dashboard** → Click **My Notesheets** card
2. All documents currently with you are displayed
3. Click **View** to see details

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

## 📁 Project Structure

```
receive_section/
├── app.py                          # Main Flask application
├── init_database.py                # Database initialization script
├── add_is_section_head_column.py  # Permission fix script
├── wbsedcl_tracking.db            # SQLite database (created on init)
├── requirements.txt               # Python dependencies
├── README.md                      # This file
│
├── templates/                     # HTML templates
│   ├── base.html                 # Base template with navigation
│   ├── login.html                # Login page
│   ├── dashboard.html            # User dashboard
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
   - Go to User Management → Edit admin
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

#### Issue: Empty dropdown when forwarding
**Solution:**
1. Check if user is current holder
2. Verify SQL query returns users (check PowerShell console for DEBUG output)
3. Check browser console (F12) for JavaScript errors

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
copies of the Software.
```

## 🎯 Roadmap

### Planned Features

- [ ] Email notifications on document forwarding
- [ ] PDF export of movement history
- [ ] Advanced search with date ranges
- [ ] Document attachments (file upload)
- [ ] Reports and analytics dashboard
- [ ] Barcode/QR code for documents

### Version History

**v1.0.0** (2026-01-12)
- Initial release
- Basic notesheet and bill tracking
- Role-based access control
- Section-wise workflow
- Movement history with time tracking
- User management
- Personalized dashboard

---

**Built with ❤️ for WBSEDCL**

*Last Updated: January 12, 2026*