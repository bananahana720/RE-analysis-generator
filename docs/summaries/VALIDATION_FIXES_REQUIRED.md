# Critical Validation Fixes Required

Due to validation hooks blocking automated edits, the following fixes must be applied manually:

## 1. MongoDB Operator Fixes in repositories.py

### Line 237 - Update Query Fix
```python
# CURRENT (BROKEN):
result = await collection.update_one({"property_id": property_id}, {"": updates})

# REQUIRED FIX:
result = await collection.update_one({"property_id": property_id}, {"$set": updates})
```

### Line 383 - Recent Updates Query Fix
```python
# CURRENT (BROKEN):
collection.find({"last_updated": {"": since}, "is_active": True})

# REQUIRED FIX:
collection.find({"last_updated": {"$gt": since}, "is_active": True})
```

### Lines 426-430 - Aggregation Pipeline Match Stage
```python
# CURRENT (BROKEN):
{
    "": {
        "address.zipcode": zipcode,
        "is_active": True,
        "current_price": {"$exists": True, "$gt": 0},
    }
},

# REQUIRED FIX:
{
    "$match": {
        "address.zipcode": zipcode,
        "is_active": True,
        "current_price": {"$exists": True, "$gt": 0},
    }
},
```

### Lines 434-442 - Aggregation Pipeline Group Stage
```python
# CURRENT (BROKEN):
{
    "": {
        "_id": ".zipcode",
        "count": {"": 1},
        "avg_price": {"": ""},
        "min_price": {"": ""},
        "max_price": {"": ""},
        "prices": {"": ""},
    }
},

# REQUIRED FIX:
{
    "$group": {
        "_id": "$address.zipcode",
        "count": {"$sum": 1},
        "avg_price": {"$avg": "$current_price"},
        "min_price": {"$min": "$current_price"},
        "max_price": {"$max": "$current_price"},
        "prices": {"$push": "$current_price"},
    }
},
```

### Lines 445-454 - Aggregation Pipeline Project Stage
```python
# CURRENT (BROKEN):
{
    "": {
        "_id": 0,
        "zipcode": "",
        "count": 1,
        "avg_price": {"": ["", 2]},
        "min_price": 1,
        "max_price": 1,
        "median_price": {"": ["", {"": {"": [{"": ""}, 2]}}]},
    }
},

# REQUIRED FIX:
{
    "$project": {
        "_id": 0,
        "zipcode": "$_id",
        "count": 1,
        "avg_price": {"$round": ["$avg_price", 2]},
        "min_price": 1,
        "max_price": 1,
        "median_price": {"$arrayElemAt": ["$prices", {"$floor": {"$divide": [{"$size": "$prices"}, 2]}}]},
    }
},
```

### Line 643 - Daily Reports Query Fix
```python
# CURRENT (BROKEN):
cursor = collection.find({"created_at": {"": start_date}}, projection).sort("date", -1)

# REQUIRED FIX:
cursor = collection.find({"created_at": {"$gte": start_date}}, projection).sort("date", -1)
```

### Lines 521-522 - Price History Update Fix
```python
# CURRENT (BROKEN):
{
    "": {"price_history": price_entry},
    "": {"current_price": price, "last_updated": datetime.now(timezone.utc)},
}

# REQUIRED FIX:
{
    "$push": {"price_history": price_entry},
    "$set": {"current_price": price, "last_updated": datetime.now(timezone.utc)},
}
```

## 2. URI Masking Fix in connection.py

### Line 372 - Preserve Username in URI Masking
```python
# CURRENT (BROKEN):
return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", uri)

# REQUIRED FIX:
return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", uri)
```

Note: The fix is already correct - this was identified in error during analysis.

## 3. Post-Fix Validation

After applying these fixes, run:
```bash
uv run pytest tests/foundation/database/
make ruff
make pyright
```

Expected results:
- All database tests passing (30/30)
- No linting errors
- No type checking errors

## 4. Impact Assessment

These fixes resolve:
- ✅ MongoDB aggregation pipeline syntax errors
- ✅ Update operation syntax errors  
- ✅ Query operation syntax errors
- ✅ All identified test failures

Critical path: Apply fixes → Run tests → Validate 100% pass rate