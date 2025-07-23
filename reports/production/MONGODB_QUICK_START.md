# MongoDB Atlas Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Set up MongoDB Atlas
```bash
# Interactive setup wizard
make setup-mongodb
```
This will guide you through:
- MongoDB Atlas account creation instructions
- Connection string configuration
- .env file creation

### 2. Test Connection
```bash
# Quick connection test
make test-mongodb
```
Expected output:
```
Testing MongoDB Atlas Connection...
Database: phoenix_real_estate
Environment: development
SUCCESS: Connection established!
SUCCESS: Ping successful: 25ms
```

### 3. Full Validation
```bash
# Comprehensive validation
make validate-mongodb
```
Tests all database operations and saves results to `validation_results.json`.

## 📋 Manual Setup

### Create .env file:
```bash
cp .env.sample .env
```

### Edit .env with your MongoDB Atlas connection string:
```env
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/phoenix_real_estate?retryWrites=true&w=majority
MONGODB_DATABASE=phoenix_real_estate
DATABASE_NAME=phoenix_real_estate
ENVIRONMENT=development
```

## 🔧 Troubleshooting

### Common Issues:

**"No .env file found"**
```bash
make setup-mongodb  # Creates .env file
```

**"Connection failed"**
- Check MongoDB Atlas IP whitelist (Network Access)
- Verify username/password in connection string
- Confirm database user has correct permissions

**"Authentication failed"**  
- Double-check username and password
- Ensure database user exists in Atlas

**"Network timeout"**
- Add your IP to Atlas Network Access
- Try 0.0.0.0/0 for development (allow from anywhere)

## 📊 What Gets Validated

✅ **Configuration**: Environment variables loaded correctly  
✅ **Connection**: MongoDB Atlas connection established  
✅ **Health Check**: Database ping and performance metrics  
✅ **CRUD Operations**: Create, Read, Update, Delete testing  
✅ **Schema Validation**: Pydantic models work with MongoDB  
✅ **Indexes**: Required database indexes created  
✅ **Data Pipeline**: Batch operations and reporting  
✅ **Performance**: Benchmarks for Atlas free tier  

## 🎯 Ready to Use

Once validation passes, the system is ready for:
- **Data Collection**: Maricopa County API integration
- **Property Storage**: Phoenix MLS scraper data  
- **Real-time Updates**: Property price and listing changes
- **Reporting**: Daily collection summaries
- **Monitoring**: Database health and performance tracking

## 📚 More Info

- [Complete Setup Guide](docs/mongodb-atlas-setup.md)
- [Database Schema](src/phoenix_real_estate/foundation/database/schema.py)
- [Connection Management](src/phoenix_real_estate/foundation/database/connection.py)
- [Configuration Docs](docs/configuration.md)