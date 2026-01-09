# WBSEDCL Tracking System - Environment Setup Guide

## Virtual Environment Created Successfully! ✓

Your Python virtual environment has been set up with all necessary dependencies for the WBSEDCL Tracking System.

## Environment Details

**Environment Name:** `wbsedcl_env`  
**Python Version:** Python 3.12  
**Location:** `./wbsedcl_env/`

## Installed Packages

### Web Framework & Core
- Flask 3.0.0 - Web framework
- Flask-Login 0.6.3 - User session management
- Flask-WTF 1.2.1 - Form handling
- WTForms 3.1.1 - Form validation
- Werkzeug 3.0.1 - WSGI utilities

### Security
- bcrypt 4.1.2 - Password hashing (production-ready)
- passlib 1.7.4 - Password hashing utilities

### Database
- SQLite3 (built-in) - Database engine

### Additional Features
- Flask-Mail 0.9.1 - Email notifications
- Flask-Session 0.5.0 - Server-side sessions
- Flask-CORS 4.0.0 - Cross-Origin Resource Sharing
- Flask-RESTful 0.3.10 - REST API development
- reportlab 4.0.9 - PDF generation
- openpyxl 3.1.2 - Excel file handling
- xlsxwriter 3.1.9 - Excel file writing
- qrcode 7.4.2 - QR code generation
- python-barcode 0.15.1 - Barcode generation
- Pillow 10.1.0 - Image processing

### Utilities
- python-dotenv 1.0.0 - Environment variable management
- python-dateutil 2.8.2 - Date/time utilities
- email-validator 2.1.0 - Email validation
- python-decouple 3.8 - Configuration management

### Development Tools
- pytest 7.4.3 - Testing framework
- pytest-flask 1.3.0 - Flask testing utilities
- flake8 7.0.0 - Code linting
- black 23.12.1 - Code formatting

### Production Servers
- gunicorn 21.2.0 - WSGI HTTP server (Linux/Mac)
- waitress 2.1.2 - WSGI server (Windows)

## How to Use the Virtual Environment

### Option 1: Automatic Setup (Recommended)

#### Linux/Mac:
```bash
bash setup_env.sh
```

#### Windows:
```cmd
setup_env.bat
```

### Option 2: Manual Activation

#### Linux/Mac:
```bash
source wbsedcl_env/bin/activate
```

#### Windows:
```cmd
wbsedcl_env\Scripts\activate.bat
```

### Option 3: Quick Activation Scripts

#### Linux/Mac:
```bash
bash activate_env.sh
```

#### Windows:
```cmd
activate_env.bat
```

## Verify Installation

Once activated, verify the installation:

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Check Flask installation
python -c "import flask; print(f'Flask version: {flask.__version__}')"
```

## Deactivate Virtual Environment

To exit the virtual environment:

```bash
deactivate
```

## Next Steps

### 1. Initialize the Database
```bash
python init_database.py
```

This will create the SQLite database with all tables and default data.

### 2. Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use any text editor
```

### 3. Run the Application
```bash
# Development mode
python app.py

# Or using Flask CLI
flask run

# Production mode (Linux/Mac)
gunicorn -w 4 -b 0.0.0.0:8000 app:app

# Production mode (Windows)
waitress-serve --port=8000 app:app
```

## Environment Configuration (.env file)

Create a `.env` file based on `.env.example`:

```ini
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_PATH=wbsedcl_tracking.db
```

**Important:** Never commit `.env` file to version control!

## Troubleshooting

### Virtual environment not activating

**Linux/Mac:**
```bash
# Make scripts executable
chmod +x setup_env.sh activate_env.sh

# Source the activation
. wbsedcl_env/bin/activate
```

**Windows:**
```cmd
# If you get execution policy error, run PowerShell as admin:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Module not found errors
```bash
# Ensure virtual environment is activated
# Then reinstall requirements
pip install -r requirements.txt
```

### Permission denied errors
```bash
# Linux/Mac - make scripts executable
chmod +x *.sh

# Windows - run as administrator
```

## Project Structure

```
wbsedcl-tracking/
├── wbsedcl_env/              # Virtual environment (don't commit)
├── wbsedcl_schema.sql        # Database schema
├── init_database.py          # Database initialization script
├── requirements.txt          # Python dependencies
├── .env.example             # Example environment variables
├── .env                     # Your environment variables (don't commit)
├── setup_env.sh             # Linux/Mac setup script
├── activate_env.sh          # Linux/Mac activation script
├── activate_env.bat         # Windows activation script
├── README.md                # Database documentation
├── ENV_SETUP_GUIDE.md       # This file
└── app.py                   # Flask application (to be created)
```

## Development Workflow

1. **Activate environment**
   ```bash
   source wbsedcl_env/bin/activate  # Linux/Mac
   wbsedcl_env\Scripts\activate.bat  # Windows
   ```

2. **Make changes to code**

3. **Run tests**
   ```bash
   pytest
   ```

4. **Check code quality**
   ```bash
   flake8 .
   black --check .
   ```

5. **Format code**
   ```bash
   black .
   ```

6. **Run application**
   ```bash
   python app.py
   ```

7. **Deactivate when done**
   ```bash
   deactivate
   ```

## Adding New Dependencies

When you need to install new packages:

```bash
# Activate environment first
source wbsedcl_env/bin/activate

# Install the package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt
```

## Updating Dependencies

To update all packages to latest versions:

```bash
# Activate environment
source wbsedcl_env/bin/activate

# Update all packages
pip install --upgrade -r requirements.txt

# Or update specific package
pip install --upgrade flask
```

## Database Management

### Initialize Database
```bash
python init_database.py
```

### Backup Database
```bash
sqlite3 wbsedcl_tracking.db ".backup wbsedcl_backup_$(date +%Y%m%d).db"
```

### Access Database CLI
```bash
sqlite3 wbsedcl_tracking.db
```

## Security Reminders

1. **Never commit `.env` file** - contains sensitive data
2. **Change default passwords immediately**
3. **Use strong SECRET_KEY** in production
4. **Enable HTTPS** in production
5. **Regular backups** of database
6. **Keep dependencies updated** for security patches

## Production Deployment Checklist

- [ ] Change DEBUG=False in .env
- [ ] Use strong SECRET_KEY
- [ ] Change default admin password
- [ ] Enable HTTPS/SSL
- [ ] Set up regular database backups
- [ ] Configure email notifications
- [ ] Set up logging
- [ ] Configure firewall
- [ ] Use gunicorn/waitress instead of Flask dev server
- [ ] Set appropriate file permissions
- [ ] Enable database encryption (if needed)

## Support & Resources

- **Flask Documentation:** https://flask.palletsprojects.com/
- **SQLite Documentation:** https://www.sqlite.org/docs.html
- **Python Documentation:** https://docs.python.org/3/

## License

Internal use only - WBSEDCL

---

**Environment Setup Complete!**  
Ready to start development.
