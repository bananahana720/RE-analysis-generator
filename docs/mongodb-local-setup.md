# MongoDB Local Setup Guide

## Overview

This guide documents the complete MongoDB local setup process for the Phoenix Real Estate Data Collector project. The project uses local MongoDB by default for development and testing, with MongoDB Atlas remaining as an optional production deployment strategy.

## System Requirements

- **Windows 10/11** (64-bit)
- **MongoDB Version**: 8.1.2 (latest 2025 version)
- **Minimum RAM**: 4GB (8GB recommended)
- **Disk Space**: 10GB minimum for data and logs

## Installation via Chocolatey

### 1. Install MongoDB

```powershell
# Run as Administrator
choco install mongodb -y
```

### 2. Verify Installation

```powershell
# Check MongoDB version
mongod --version
```

Expected output:
```
db version v8.1.2
Build Info: {
    "version": "8.1.2",
    "gitVersion": "..."
}
```

## Directory Structure

MongoDB uses the following directory structure on Windows:

- **Installation Path**: `C:\Program Files\MongoDB\Server\8.1\bin`
- **Data Directory**: `C:\data\db`
- **Log Directory**: `C:\data\log`
- **Configuration File**: `C:\Program Files\MongoDB\Server\8.1\bin\mongod.cfg`

## Service Configuration

### Service Details

- **Service Name**: MongoDB
- **Service Display Name**: MongoDB Server
- **Startup Type**: Automatic
- **Log File**: `C:\data\log\mongod.log`

### Service Management Commands

```powershell
# Start MongoDB service
net start MongoDB

# Stop MongoDB service
net stop MongoDB

# Check service status
sc query MongoDB

# Set service to automatic startup
sc config MongoDB start=auto
```

## Setup Scripts

### Automated Setup Script

The project includes an automated setup script:

**Location**: `scripts/setup/start_mongodb_service.bat`

```batch
@echo off
echo Starting MongoDB service setup...

REM Create data directories if they don't exist
if not exist "C:\data\db" mkdir "C:\data\db"
if not exist "C:\data\log" mkdir "C:\data\log"

REM Start MongoDB service
net start MongoDB

REM Verify service is running
sc query MongoDB | find "RUNNING"
if %errorlevel% neq 0 (
    echo ERROR: MongoDB service failed to start
    exit /b 1
)

echo MongoDB service started successfully
```

### Connection Testing Script

**Location**: `scripts/testing/test_mongodb_connection.py`

```python
import pymongo
import sys

def test_connection():
    """Test MongoDB connection and setup database."""
    try:
        # Connect to local MongoDB
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        
        # Test connection
        client.admin.command('ping')
        print("✓ MongoDB connection successful")
        
        # Create database and collections
        db = client["phoenix_real_estate"]
        
        # Create collections with indexes
        collections = {
            "properties": [
                ("property_id", pymongo.ASCENDING),
                ("address.zip", pymongo.ASCENDING),
                ("last_updated", pymongo.DESCENDING)
            ],
            "collection_history": [
                ("timestamp", pymongo.DESCENDING),
                ("status", pymongo.ASCENDING)
            ],
            "errors": [
                ("timestamp", pymongo.DESCENDING),
                ("error_type", pymongo.ASCENDING)
            ]
        }
        
        for collection_name, indexes in collections.items():
            collection = db[collection_name]
            for index in indexes:
                collection.create_index([index])
            print(f"✓ Created collection: {collection_name}")
        
        print("\n✓ MongoDB setup complete!")
        return True
        
    except Exception as e:
        print(f"✗ MongoDB connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
```

## Database Configuration

### Database Name
- **Primary Database**: `phoenix_real_estate`

### Collections

1. **properties**
   - Stores real estate property data
   - Indexes:
     - `property_id` (ascending) - unique identifier
     - `address.zip` (ascending) - for location-based queries
     - `last_updated` (descending) - for recent data queries

2. **collection_history**
   - Tracks data collection runs
   - Indexes:
     - `timestamp` (descending) - for chronological queries
     - `status` (ascending) - for filtering by collection status

3. **errors**
   - Logs collection and processing errors
   - Indexes:
     - `timestamp` (descending) - for recent error queries
     - `error_type` (ascending) - for error categorization

### Index Configuration

All indexes are configured for optimal query performance:

```javascript
// Properties collection indexes
db.properties.createIndex({ "property_id": 1 }, { unique: true })
db.properties.createIndex({ "address.zip": 1 })
db.properties.createIndex({ "last_updated": -1 })
db.properties.createIndex({ "prices.date": -1 })

// Collection history indexes
db.collection_history.createIndex({ "timestamp": -1 })
db.collection_history.createIndex({ "status": 1 })

// Errors collection indexes
db.errors.createIndex({ "timestamp": -1 })
db.errors.createIndex({ "error_type": 1 })
```

## Application Connection

### Connection String
```
mongodb://localhost:27017/phoenix_real_estate
```

### Python Connection Example
```python
from pymongo import MongoClient

# Create connection
client = MongoClient("mongodb://localhost:27017/")
db = client["phoenix_real_estate"]

# Access collections
properties = db["properties"]
history = db["collection_history"]
errors = db["errors"]
```

## Troubleshooting

### Common Issues and Solutions

#### 1. MongoDB Service Won't Start

**Symptoms**: Service fails to start, error 1067

**Solutions**:
- Check if port 27017 is already in use: `netstat -an | findstr :27017`
- Verify data directory exists and has write permissions
- Check Windows Event Viewer for detailed error messages
- Run MongoDB manually to see error output: `mongod --dbpath C:\data\db`

#### 2. Connection Refused Error

**Symptoms**: `pymongo.errors.ServerSelectionTimeoutError`

**Solutions**:
- Ensure MongoDB service is running: `sc query MongoDB`
- Check Windows Firewall isn't blocking port 27017
- Verify MongoDB is listening on localhost: `netstat -an | findstr :27017`

#### 3. Permission Denied Errors

**Symptoms**: Cannot create database or write data

**Solutions**:
- Ensure your user has permissions to `C:\data\db`
- Run MongoDB service under an account with appropriate permissions
- Check antivirus software isn't blocking MongoDB

#### 4. Disk Space Issues

**Symptoms**: Write operations fail, database stops accepting connections

**Solutions**:
- Check available disk space on C: drive
- Configure MongoDB to use a different data directory with more space
- Enable log rotation to prevent log file growth

### Verification Commands

```powershell
# Check if MongoDB is installed
where mongod

# Check service status
sc query MongoDB

# Test MongoDB shell connection
mongo --eval "db.adminCommand('ping')"

# Check listening ports
netstat -an | findstr :27017

# View recent log entries
type "C:\data\log\mongod.log" | more
```

## Performance Optimization

### Recommended Settings

1. **Memory**: Allocate at least 2GB for WiredTiger cache
2. **Journal**: Enable journaling for data durability
3. **Compression**: Use snappy compression (default)

### Configuration File

Create or modify `C:\Program Files\MongoDB\Server\8.1\bin\mongod.cfg`:

```yaml
systemLog:
  destination: file
  path: C:\data\log\mongod.log
  logAppend: true

storage:
  dbPath: C:\data\db
  journal:
    enabled: true
  engine: wiredTiger
  wiredTiger:
    engineConfig:
      cacheSizeGB: 2

net:
  port: 27017
  bindIp: 127.0.0.1

processManagement:
  windowsService:
    serviceName: MongoDB
    displayName: MongoDB Server
    description: MongoDB Server Instance
```

## Migration from Atlas

If migrating from MongoDB Atlas to local:

1. Export data from Atlas:
   ```bash
   mongodump --uri="mongodb+srv://..." --out=atlas_backup
   ```

2. Import to local MongoDB:
   ```bash
   mongorestore --host=localhost:27017 atlas_backup
   ```

3. Update application connection strings from Atlas URI to local URI

## Security Considerations

For local development:
- MongoDB runs without authentication by default
- Only accessible from localhost (127.0.0.1)
- No external network access

For production local deployments:
- Enable authentication
- Configure SSL/TLS
- Implement IP whitelisting
- Regular backups

## Next Steps

1. Run the setup script: `scripts\setup\start_mongodb_service.bat`
2. Test connection: `python scripts\testing\test_mongodb_connection.py`
3. Configure your application to use `mongodb://localhost:27017/phoenix_real_estate`
4. Start developing!

## Related Documentation

- [MongoDB Atlas Setup](./mongodb-atlas-setup.md) - For cloud deployment option
- [Configuration Guide](./configuration.md) - Application configuration details
- [Production Setup](./production-setup.md) - Production deployment considerations