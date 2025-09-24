# InvApp - Recreation Inventory Management System

A comprehensive inventory management system developed for the MCC Windham Recreation Department. This application allows staff and residents to efficiently track equipment, manage users, and generate detailed reports. Developed by Arthur Belanger ([MusicalViking](https://github.com/MusicalViking)) to streamline inventory management and reporting processes.

## Overview

InvApp is a powerful, web-based inventory management solution specifically designed for recreation departments. It provides a user-friendly interface for tracking equipment, managing personnel, and generating comprehensive reports to support operational efficiency and accountability.

## Key Features

### 📦 **Inventory Management**
- Add, edit, and delete inventory items with comprehensive details
- Track equipment by category, location, condition, and status
- Real-time inventory monitoring and alerts
- Equipment assignment and tracking

### 👥 **User Management**
- Role-based access control system
- Admin dashboard for managing employees and permissions
- Secure authentication with password policies
- User profile management and access logging

### 📊 **Dashboard & Analytics**
- Visual overview of inventory statistics and distribution
- Interactive charts and graphs using Plotly
- Real-time data visualization
- Inventory trends and usage patterns

### 📋 **Reporting System**
- Generate PDF and Excel reports
- Customizable report templates
- Automated report scheduling
- Export capabilities for various formats

### 💬 **Communication Tools**
- Built-in post box for staff communication
- Internal messaging system
- Notification and alert system
- Activity logging and audit trails

### 🔒 **Security & Compliance**
- Role-based access control (RBAC)
- Password strength validation and history tracking
- Password expiry and reset functionality
- Secure data encryption and backup systems

### 💾 **Data Management**
- Automated database backup system
- SQLite database with robust data integrity
- Data import/export capabilities
- System monitoring and performance tracking

## Technology Stack

- **Frontend**: Streamlit (Python web framework)
- **Database**: SQLite with custom ORM
- **Data Processing**: Pandas for data manipulation
- **Visualization**: Plotly for interactive charts
- **Security**: bcrypt for password hashing, pyotp for 2FA
- **Reporting**: ReportLab for PDF generation, openpyxl for Excel
- **Utilities**: Schedule for automated tasks, psutil for system monitoring

## Installation & Setup

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)
- SQLite (included with Python)

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ArthurBelanger207/recreation-inventory.git
   cd recreation-inventory
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   - Copy `.env.example` to `.env`
   - Update configuration values as needed

5. **Initialize database:**
   ```bash
   python -c "from db_manager import initialize_db; initialize_db()"
   ```

6. **Launch application:**
   ```bash
   streamlit run app.py
   ```

### Default Credentials
- **Username**: admin
- **Password**: password123

*You will be prompted to change the default password on first login.*

## Project Structure

```
InvApp/
├── app.py                # Main application entry point
├── config.py             # Configuration settings and constants
├── auth.py               # User authentication and authorization
├── models.py             # Database models and business logic
├── db_manager.py         # Database connection and management
├── db_utils.py           # Database utility functions
├── pdf_generator.py      # PDF report generation
├── ui_components.py      # Reusable UI components
├── ui_dialogs.py         # Dialog components and modals
├── logging_config.py     # Logging configuration
├── simple_backup.py      # Database backup functionality
├── backup_scheduler.py   # Automated backup scheduling
├── reset_admin.py        # Admin account reset utility
├── reset_password.py     # Password reset functionality
├── test.py               # Test scripts
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── LICENSE               # MIT License
└── README.md             # This file
```

## Development Philosophy

This application demonstrates several key development principles:

- **User-Centric Design**: Intuitive interface designed specifically for recreation department staff
- **Security First**: Comprehensive security measures including encryption, access control, and audit trails
- **Scalability**: Built to handle growing inventory and user bases
- **Maintainability**: Clean, modular code structure with comprehensive documentation
- **Reliability**: Automated backup systems and error handling
- **Performance**: Optimized queries and efficient data processing

## Contributing

This project follows modern development practices with:
- Modular architecture for easy maintenance
- Comprehensive logging and error handling
- Automated testing capabilities
- Clear documentation and code comments

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support & Maintenance

The system includes:
- Automated backup scheduling
- System monitoring and performance tracking
- Comprehensive logging for troubleshooting
- Admin utilities for account management

---

_Built and maintained by Arthur Belanger ([MusicalViking](https://github.com/MusicalViking))_

*Designed specifically for the MCC Windham Recreation Department to streamline inventory management and enhance operational efficiency.*
