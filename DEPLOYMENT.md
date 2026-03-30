# Recreation Inventory Management System

---

# DEPLOYMENT.md file for Streamlit UI

---

# Author: github/coding-with-arty

# Recreation Inventory System Deployment Guide

This document provides instructions for deploying the Recreation Inventory Management System to a production environment using Docker.

## Prerequisites

- Docker and Docker Compose installed on the production server
- Git for code repository access
- At least 1GB of RAM and 5GB of disk space

## Deployment Steps

### 1. Clone the Repository

```bash
git clone https://github.com/ArthurBelanger207/recreation-inventory.git
cd RecInvApp
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with the following contents, replacing placeholders with your actual values:

```
# Database Configuration
DB_PATH=/app/data/inventory.db

# Admin Configuration
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
ADMIN_FIRST_NAME=Admin
ADMIN_LAST_NAME=User

# Security Settings
PASSWORD_EXPIRY_DAYS=60
MIN_PASSWORD_LENGTH=12
PASSWORD_HISTORY_LIMIT=10
SESSION_EXPIRY_HOURS=12

# Logging Configuration
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE=/app/logs/app.log

# Backup Configuration
BACKUP_DIR=/app/backups

# Application Settings
DEBUG_MODE=false
ALLOWED_EXTENSIONS=png,pdf
MAX_UPLOAD_SIZE_MB=5

# SMTP Configuration (Optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_smtp_password
SMTP_FROM_EMAIL=inventory@example.com
```

### 3. Build and Start the Docker Container

Use Docker Compose to build and start the application:

```bash
docker-compose up -d --build
```

This will:

- Build the Docker image using the Dockerfile
- Start the container in detached mode
- Mount volumes for data, logs, and backups
- Expose the application on port 8501

### 4. Access the Application

Once deployed, you can access the application at:

```
http://your-server-address:8501
```

### 5. Initial Login

Log in with the admin credentials you configured in the `.env` file:

- Username: admin (or whatever you set in ADMIN_USERNAME)
- Password: password123 (from ADMIN_PASSWORD)

You will be prompted to change the password on first login.

## Maintenance

### Backups

Backups are stored in the `backups` directory and are taken automatically every 24 hours.

To manually create a backup, you can use the admin dashboard or run:

```bash
docker exec recreation-inventory-app python -c "from backup_scheduler import get_backup_manager; get_backup_manager().create_backup()"
```

### Viewing Logs

Logs are stored in the `logs` directory. You can view them with:

```bash
docker exec recreation-inventory-app tail -f /app/logs/app.log
```

### Updating the Application

To update the application:

```bash
git pull  # Get the latest code
docker-compose down
docker-compose up -d --build
```

## Troubleshooting

### Database Issues

If you encounter database issues, you can run the health check:

```bash
docker exec Recreation-inventory-app python -c "from db_utils import check_db_health; print(check_db_health())"
```

### Container Issues

If the container fails to start, check logs:

```bash
docker logs recreation-inventory-app
```

### Common Fixes

- **Permission issues**: Ensure the directories have proper permissions

  ```bash
  chmod -R 755 data logs backups
  ```

- **Database corruption**: Restore from a backup using the admin interface

- **Memory issues**: Increase container memory limit in docker-compose.yml:
  ```yaml
  services:
    invapp:
      deploy:
        resources:
          limits:
            memory: 2G
  ```

## Security Considerations

1. **Environment Variables**: Never commit the `.env` file to version control
2. **HTTPS**: In production, set up a reverse proxy (Nginx/Apache) with SSL
3. **Firewall**: Restrict access to port 8501 to trusted networks
4. **Regular Updates**: Keep the application and dependencies updated
5. **Backup Verification**: Regularly test restoring from backups
6. **Password Policy**: Enforce strong password requirements

## Production Checklist

Before going live, ensure you have:

- [ ] Configured secure admin credentials
- [ ] Set up HTTPS/SSL
- [ ] Implemented a backup strategy
- [ ] Tested the restore process
- [ ] Validated all file paths
- [ ] Set appropriate permission settings
- [ ] Configured logging
- [ ] Updated all dependencies to secure versions
- [ ] Removed any development/debug settings
- [ ] Tested on the production environment
