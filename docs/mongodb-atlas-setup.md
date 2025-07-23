# MongoDB Atlas Setup Guide

This guide will help you set up MongoDB Atlas connectivity for the Phoenix Real Estate Data Collection System.

## 🏗️ MongoDB Atlas Setup

### Step 1: Create MongoDB Atlas Account

1. Go to [MongoDB Atlas](https://cloud.mongodb.com/)
2. Create a free account or sign in
3. You'll be prompted to create your first cluster

### Step 2: Create a Cluster

1. Choose **M0 Sandbox** (Free tier)
2. Select a cloud provider and region (closest to your location)
3. Name your cluster (e.g., "phoenix-real-estate")
4. Click "Create Cluster"
5. Wait 5-10 minutes for cluster provisioning

### Step 3: Create Database User

1. In the Atlas dashboard, click **Database Access**
2. Click **Add New Database User**
3. Choose **Password** authentication method
4. Enter a username (e.g., "phoenix_user")
5. Generate a strong password and save it securely
6. Select database user privileges:
   - **Built-in Role**: Choose "Atlas admin" for full access
   - Or **Custom Role**: "readWriteAnyDatabase" for more restricted access
7. Click **Add User**

### Step 4: Configure Network Access

1. Go to **Network Access**
2. Click **Add IP Address**
3. For development:
   - Click **Allow Access from Anywhere** (0.0.0.0/0)
   - ⚠️ **Warning**: This allows connections from any IP address
4. For production:
   - Add your specific IP addresses
   - Click **Add Current IP Address** for your current location
5. Click **Confirm**

### Step 5: Get Connection String

1. Go back to **Clusters**
2. Click **Connect** on your cluster
3. Choose **Connect your application**
4. Select **Python** as driver and **3.6 or later** as version
5. Copy the connection string
6. Replace `<password>` with your database user password
7. Replace `<dbname>` with `phoenix_real_estate`

Your connection string should look like:
```
mongodb+srv://phoenix_user:your_password@cluster0.xxxxx.mongodb.net/phoenix_real_estate?retryWrites=true&w=majority
```

## 🔧 Local Configuration

### Option 1: Interactive Setup (Recommended)

Run the interactive setup script:

```bash
python scripts/setup_mongodb_atlas.py
```

This script will:
- Guide you through MongoDB Atlas setup
- Help you create the `.env` file
- Validate your connection string format
- Create the proper configuration

### Option 2: Manual Setup

1. Copy the sample environment file:
   ```bash
   cp .env.sample .env
   ```

2. Edit `.env` file and update the MongoDB configuration:
   ```env
   # Replace with your actual MongoDB Atlas connection string
   MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/phoenix_real_estate?retryWrites=true&w=majority
   MONGODB_DATABASE=phoenix_real_estate
   DATABASE_NAME=phoenix_real_estate
   ```

3. Set other required variables:
   ```env
   ENVIRONMENT=development
   LOG_LEVEL=INFO
   SECRET_KEY=development-secret-key-change-in-production
   ```

## ✅ Connection Validation

### Quick Connection Test

Run a quick connection test:

```bash
python scripts/test_db_connection.py
```

This will:
- ✅ Verify configuration loading
- ✅ Test MongoDB Atlas connection
- ✅ Perform a basic ping test
- ✅ Show database statistics

### Full Validation Suite

For comprehensive validation, run:

```bash
python scripts/validate_mongodb_atlas.py
```

This comprehensive test includes:
- ✅ Configuration validation
- ✅ Database connection
- ✅ Health check with performance metrics
- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ Pydantic schema validation
- ✅ Database index validation
- ✅ Data pipeline simulation
- ✅ Performance benchmarking

## 🗂️ Database Schema

The system will automatically create the following collections:

### Properties Collection
```javascript
{
  property_id: "unique_identifier",
  address: {
    street: "123 Main St",
    city: "Phoenix", 
    state: "AZ",
    zipcode: "85001"
  },
  current_price: 450000.0,
  features: {
    bedrooms: 3,
    bathrooms: 2.5,
    square_feet: 2100
  },
  listing: {
    status: "active",
    mls_id: "MLS123456"
  },
  sources: [{
    source: "phoenix_mls",
    collected_at: "2025-01-20T10:00:00Z"
  }],
  last_updated: "2025-01-20T10:00:00Z",
  is_active: true
}
```

### Daily Reports Collection
```javascript
{
  date: "2025-01-20T00:00:00Z",
  total_properties_processed: 150,
  new_properties_found: 25,
  properties_by_source: {
    "phoenix_mls": 100,
    "maricopa_county": 50
  },
  price_statistics: {
    "min": 200000,
    "max": 1200000,
    "avg": 485000
  }
}
```

## 🔍 Indexes

The system automatically creates optimized indexes:

**Properties Collection:**
- `property_id` (unique)
- `address.zipcode` 
- `address.street`
- `listing.status`
- `current_price`
- `last_updated`
- `is_active`
- Compound indexes for common queries

**Daily Reports Collection:**
- `date` (unique)

## 🚨 Troubleshooting

### Common Connection Issues

1. **Authentication Failed**
   - Verify username and password in connection string
   - Check that database user exists and has correct permissions

2. **Network Timeout**
   - Verify IP address is whitelisted in Network Access
   - Check firewall settings
   - Try allowing access from anywhere (0.0.0.0/0) for testing

3. **Database Not Found**
   - The database will be created automatically when first document is inserted
   - Verify database name matches in connection string and config

4. **SSL/TLS Errors**
   - Ensure you're using `mongodb+srv://` for Atlas connections
   - Check that `retryWrites=true&w=majority` is in connection string

### Testing with Sample Data

Run the data pipeline test:

```bash
# This will create sample properties and test all operations
python scripts/validate_mongodb_atlas.py
```

### Monitoring Connection Health

The system provides health check endpoints:

```python
from phoenix_real_estate.foundation.database.connection import get_database_connection

# Get connection
conn = await get_database_connection(uri, database_name)

# Check health
health = await conn.health_check()
print(f"Connected: {health['connected']}")
print(f"Ping time: {health['ping_time_ms']}ms")
```

## 🎯 Next Steps

Once MongoDB Atlas is configured and validated:

1. **Run the test suite**:
   ```bash
   uv run pytest tests/foundation/database/ -v
   ```

2. **Start the data collection pipeline**:
   ```bash
   python -m phoenix_real_estate.collectors.maricopa.collector
   ```

3. **Monitor with logs**:
   ```bash
   tail -f logs/application.log
   ```

4. **Set up monitoring** (optional):
   ```bash
   docker-compose -f config/monitoring/docker-compose.yml up -d
   ```

## 📚 Additional Resources

- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com/)
- [Motor (Async MongoDB Driver) Documentation](https://motor.readthedocs.io/)
- [Phoenix Real Estate Architecture](docs/architecture/architecture.md)
- [Configuration Management](docs/configuration.md)
- [Secrets Management](docs/secrets-management.md)

## 🔐 Security Best Practices

1. **Use strong passwords** for database users
2. **Whitelist specific IP addresses** in production
3. **Rotate database credentials** regularly
4. **Enable audit logs** in MongoDB Atlas
5. **Use separate clusters** for development and production
6. **Monitor connection logs** for suspicious activity

## 📊 Atlas Free Tier Limits

- **Storage**: 512 MB
- **RAM**: Shared
- **Connections**: 100 concurrent
- **Data Transfer**: No limit on outbound data transfer
- **Clusters**: 1 per project

For production workloads, consider upgrading to a dedicated cluster.