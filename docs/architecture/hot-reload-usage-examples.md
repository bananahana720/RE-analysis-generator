# Hot-Reload Configuration - Usage Examples

## Table of Contents
1. [Basic Usage](#basic-usage)
2. [Component Integration](#component-integration)
3. [Advanced Patterns](#advanced-patterns)
4. [Development Workflows](#development-workflows)
5. [Troubleshooting](#troubleshooting)

## Basic Usage

### Simple Setup

```python
from phoenix_real_estate.foundation.config import HotReloadableConfigProvider

# Initialize with hot-reload enabled (auto-detects development environment)
config = HotReloadableConfigProvider()

# Check if hot-reload is active
if config.hot_reload.is_enabled():
    print("Hot-reload is active!")
    print(f"Watching: {config.hot_reload.get_watch_paths()}")

# Get configuration values as usual
db_uri = config.get("database.uri")
log_level = config.get("logging.level")

# The configuration will automatically update when files change!
```

### Manual Control

```python
# Explicitly enable/disable hot-reload
config = HotReloadableConfigProvider(enable_hot_reload=True)

# Disable temporarily
config.hot_reload.disable()

# Re-enable
config.hot_reload.enable()

# Force immediate reload
result = config.hot_reload.reload_now()
if result.success:
    print(f"Reloaded {len(result.changes)} changes")
else:
    print(f"Reload failed: {result.errors}")
```

### Watching Specific Values

```python
# Watch a specific configuration value
def on_timeout_change(key: str, old_value: Any, new_value: Any):
    print(f"API timeout changed from {old_value} to {new_value}")

handle = config.watch_value("api.timeout", on_timeout_change)

# Later, stop watching
config.unwatch(handle)

# Watch multiple values with pattern
def on_database_change(key: str, old_value: Any, new_value: Any):
    print(f"Database config changed: {key}")

db_handle = config.watch_pattern("database.*", on_database_change)
```

## Component Integration

### Database Connection Pool

```python
from phoenix_real_estate.foundation.config import ConfigSubscriber
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

class HotReloadableMongoDBPool(ConfigSubscriber):
    """MongoDB connection pool with hot-reload support."""
    
    def __init__(self, config: HotReloadableConfigProvider):
        self.config = config
        self.client = None
        self.db = None
        
        # Subscribe to database configuration changes
        config.hot_reload.subscribe("database", self)
        
        # Initialize connection
        self._connect()
    
    def _connect(self):
        """Create MongoDB connection."""
        uri = self.config.get_required("database.uri")
        db_name = self.config.get_required("database.name")
        pool_size = self.config.get_typed("database.max_pool_size", int, 10)
        
        # Close existing connection if any
        if self.client:
            self.client.close()
        
        # Create new connection
        self.client = AsyncIOMotorClient(
            uri,
            maxPoolSize=pool_size,
            minPoolSize=1
        )
        self.db = self.client[db_name]
        
        print(f"Connected to MongoDB: {db_name} (pool size: {pool_size})")
    
    def on_config_change(self, path: str, old_value: Any, new_value: Any):
        """Handle database configuration changes."""
        if path in ("database.uri", "database.name"):
            # Critical change - reconnect
            print(f"Database {path} changed, reconnecting...")
            self._connect()
        elif path == "database.max_pool_size":
            # Pool size change - adjust pool
            print(f"Pool size changed from {old_value} to {new_value}")
            self._connect()  # Motor requires reconnection for pool changes
    
    def on_reload_error(self, error: Exception, changes: List[ConfigChange]):
        """Handle reload errors gracefully."""
        print(f"Configuration reload failed: {error}")
        print("Continuing with current database configuration")
    
    async def get_collection(self, name: str):
        """Get a collection from the database."""
        return self.db[name]
    
    def close(self):
        """Close connections and cleanup."""
        if self.client:
            self.client.close()

# Usage
config = HotReloadableConfigProvider()
db_pool = HotReloadableMongoDBPool(config)

# Now database configuration changes are automatically applied!
```

### Logging Configuration

```python
import logging
import logging.handlers
from pathlib import Path

class HotReloadableLogger(ConfigSubscriber):
    """Logger with hot-reload configuration support."""
    
    def __init__(self, config: HotReloadableConfigProvider, name: str = None):
        self.config = config
        self.logger = logging.getLogger(name)
        self.handlers = {}
        
        # Subscribe to logging configuration
        config.hot_reload.subscribe("logging", self)
        
        # Initial setup
        self._configure_logging()
    
    def _configure_logging(self):
        """Configure logging based on current configuration."""
        # Get configuration
        level = self.config.get("logging.level", "INFO")
        format_str = self.config.get("logging.format", 
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_enabled = self.config.get_typed("logging.console_output", bool, True)
        file_path = self.config.get("logging.file_path")
        
        # Set level
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Create formatter
        formatter = logging.Formatter(format_str)
        
        # Remove old handlers
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
            handler.close()
        
        # Console handler
        if console_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler
        if file_path:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Rotating file handler
            max_bytes = self.config.get_typed("logging.max_file_size_mb", int, 10) * 1024 * 1024
            backup_count = self.config.get_typed("logging.backup_count", int, 5)
            
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        self.logger.info(f"Logging configured: level={level}, console={console_enabled}")
    
    def on_config_change(self, path: str, old_value: Any, new_value: Any):
        """Handle logging configuration changes."""
        self.logger.info(f"Logging configuration changed: {path}")
        
        # Reconfigure logging
        self._configure_logging()
        
        # Log the change with new configuration
        self.logger.info(f"Applied logging change: {path} = {new_value}")

# Usage
config = HotReloadableConfigProvider()
logger_mgr = HotReloadableLogger(config, "phoenix_real_estate")
logger = logger_mgr.logger

# Now logging configuration changes are automatically applied!
logger.info("This will use the current configuration")

# Change logging level in config file...
# The logger will automatically adjust!
```

### Rate Limiter

```python
import time
import threading
from collections import deque
from datetime import datetime, timedelta

class HotReloadableRateLimiter(ConfigSubscriber):
    """Rate limiter with hot-reload configuration."""
    
    def __init__(self, config: HotReloadableConfigProvider, key_prefix: str = "collection"):
        self.config = config
        self.key_prefix = key_prefix
        self.requests = deque()
        self.lock = threading.Lock()
        
        # Configuration
        self.max_requests = None
        self.window_minutes = None
        self.min_delay = None
        
        # Subscribe to rate limiting configuration
        config.hot_reload.subscribe(f"{key_prefix}.rate_limiting", self)
        config.hot_reload.subscribe(f"{key_prefix}.max_requests_per_hour", self)
        config.hot_reload.subscribe(f"{key_prefix}.min_request_delay", self)
        
        # Initial configuration
        self._load_config()
    
    def _load_config(self):
        """Load rate limiting configuration."""
        # Check if rate limiting is enabled
        enabled = self.config.get_typed(f"{self.key_prefix}.rate_limiting.enabled", bool, True)
        
        if enabled:
            self.max_requests = self.config.get_typed(
                f"{self.key_prefix}.max_requests_per_hour", int, 100
            )
            self.window_minutes = self.config.get_typed(
                f"{self.key_prefix}.rate_limiting.window_size_minutes", int, 60
            )
            self.min_delay = self.config.get_typed(
                f"{self.key_prefix}.min_request_delay", float, 3.6
            )
        else:
            # Disable rate limiting
            self.max_requests = float('inf')
            self.window_minutes = 60
            self.min_delay = 0
        
        print(f"Rate limiter configured: {self.max_requests} requests per {self.window_minutes} minutes")
    
    def on_config_change(self, path: str, old_value: Any, new_value: Any):
        """Handle rate limiting configuration changes."""
        print(f"Rate limiting config changed: {path}")
        self._load_config()
    
    def can_make_request(self) -> tuple[bool, float]:
        """
        Check if a request can be made.
        
        Returns:
            Tuple of (can_make_request, wait_time_seconds)
        """
        with self.lock:
            now = datetime.now()
            
            # Clean old requests
            cutoff = now - timedelta(minutes=self.window_minutes)
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            
            # Check rate limit
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest = self.requests[0]
                wait_until = oldest + timedelta(minutes=self.window_minutes)
                wait_seconds = (wait_until - now).total_seconds()
                return False, max(0, wait_seconds)
            
            # Check minimum delay
            if self.requests and self.min_delay > 0:
                last_request = self.requests[-1]
                elapsed = (now - last_request).total_seconds()
                if elapsed < self.min_delay:
                    return False, self.min_delay - elapsed
            
            return True, 0
    
    def record_request(self):
        """Record that a request was made."""
        with self.lock:
            self.requests.append(datetime.now())
    
    def wait_if_needed(self) -> float:
        """
        Wait if necessary before making a request.
        
        Returns:
            Time waited in seconds.
        """
        can_request, wait_time = self.can_make_request()
        
        if not can_request and wait_time > 0:
            print(f"Rate limited, waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
            return wait_time
        
        return 0

# Usage
config = HotReloadableConfigProvider()
rate_limiter = HotReloadableRateLimiter(config)

# Make requests with rate limiting
for i in range(10):
    # Wait if rate limited
    wait_time = rate_limiter.wait_if_needed()
    
    # Make the request
    print(f"Making request {i+1}")
    # ... actual request code ...
    
    # Record the request
    rate_limiter.record_request()

# Rate limits will automatically adjust when configuration changes!
```

## Advanced Patterns

### Conditional Hot-Reload

```python
class ConditionalHotReload:
    """Example of conditional hot-reload based on environment."""
    
    def __init__(self, config: HotReloadableConfigProvider):
        self.config = config
        
        # Only enable hot-reload in specific environments
        if config.get_environment() in ["development", "testing"]:
            # Enable with custom options
            config.hot_reload.enable()
            
            # Add custom validation
            config.hot_reload.add_validator(self._validate_safe_changes)
        else:
            print("Hot-reload disabled in production")
    
    def _validate_safe_changes(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate that changes are safe for hot-reload."""
        errors = []
        
        # Don't allow database URI changes in testing
        if self.config.get_environment() == "testing":
            current_uri = self.config.get("database.uri")
            new_uri = config.get("database", {}).get("uri")
            
            if current_uri != new_uri:
                errors.append(ValidationError(
                    path="database.uri",
                    message="Database URI cannot be changed in testing environment",
                    constraint="immutable in testing",
                    actual_value=new_uri
                ))
        
        return errors
```

### Grouped Configuration Updates

```python
class GroupedConfigUpdates(ConfigSubscriber):
    """Handle related configuration changes together."""
    
    def __init__(self, config: HotReloadableConfigProvider):
        self.config = config
        self.pending_changes = {}
        self.change_timer = None
        
        # Subscribe to multiple related paths
        config.hot_reload.subscribe("api", self)
        config.hot_reload.subscribe("proxy", self)
    
    def on_config_change(self, path: str, old_value: Any, new_value: Any):
        """Collect related changes."""
        self.pending_changes[path] = (old_value, new_value)
        
        # Cancel existing timer
        if self.change_timer:
            self.change_timer.cancel()
        
        # Set new timer to apply changes together
        self.change_timer = threading.Timer(0.5, self._apply_changes)
        self.change_timer.start()
    
    def _apply_changes(self):
        """Apply all pending changes together."""
        if not self.pending_changes:
            return
        
        print(f"Applying {len(self.pending_changes)} configuration changes together:")
        
        # Check if we need to recreate connections
        needs_reconnect = any(
            path.startswith("proxy") 
            for path in self.pending_changes
        )
        
        if needs_reconnect:
            print("Proxy configuration changed, recreating connections...")
            # Recreate all connections with new proxy settings
            self._recreate_connections()
        else:
            # Apply individual changes
            for path, (old, new) in self.pending_changes.items():
                print(f"  {path}: {old} → {new}")
        
        self.pending_changes.clear()
```

### Configuration Migration

```python
class ConfigMigration:
    """Handle configuration format migrations during hot-reload."""
    
    def __init__(self, config: HotReloadableConfigProvider):
        self.config = config
        self.version_key = "config_version"
        
        # Add pre-reload hook for migrations
        config.hot_reload.add_pre_reload_hook(self._migrate_config)
    
    def _migrate_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate configuration to latest format."""
        current_version = self.config.get(self.version_key, 1)
        new_version = new_config.get(self.version_key, 1)
        
        if new_version > current_version:
            print(f"Migrating configuration from v{current_version} to v{new_version}")
            
            # Apply migrations
            if current_version < 2 and new_version >= 2:
                new_config = self._migrate_v1_to_v2(new_config)
            
            if current_version < 3 and new_version >= 3:
                new_config = self._migrate_v2_to_v3(new_config)
        
        return new_config
    
    def _migrate_v1_to_v2(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v1 to v2 format."""
        # Example: Rename old keys to new format
        if "api_key" in config:
            config["api"] = {"key": config.pop("api_key")}
        
        return config
    
    def _migrate_v2_to_v3(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v2 to v3 format."""
        # Example: Convert string to structured format
        if "database" in config and isinstance(config["database"], str):
            config["database"] = {"uri": config["database"]}
        
        return config
```

## Development Workflows

### Interactive Configuration Testing

```python
class ConfigTester:
    """Interactive configuration testing tool."""
    
    def __init__(self, config: HotReloadableConfigProvider):
        self.config = config
    
    def test_value(self, key: str):
        """Test configuration value changes."""
        print(f"\nTesting configuration key: {key}")
        print(f"Current value: {self.config.get(key)}")
        
        # Watch for changes
        changes = []
        
        def capture_change(k, old, new):
            changes.append((k, old, new))
            print(f"Change detected: {old} → {new}")
        
        handle = self.config.watch_value(key, capture_change)
        
        print("Modify the configuration file and save it...")
        print("Press Enter when done testing")
        input()
        
        # Cleanup
        self.config.unwatch(handle)
        
        print(f"\nTotal changes detected: {len(changes)}")
        return changes
    
    def benchmark_reload(self, iterations: int = 10):
        """Benchmark hot-reload performance."""
        import time
        
        print(f"\nBenchmarking hot-reload ({iterations} iterations)...")
        
        times = []
        for i in range(iterations):
            start = time.time()
            result = self.config.hot_reload.reload_now()
            elapsed = time.time() - start
            
            times.append(elapsed)
            print(f"Iteration {i+1}: {elapsed*1000:.2f}ms")
        
        avg_time = sum(times) / len(times)
        print(f"\nAverage reload time: {avg_time*1000:.2f}ms")

# Usage
config = HotReloadableConfigProvider()
tester = ConfigTester(config)

# Test specific value
tester.test_value("logging.level")

# Benchmark performance
tester.benchmark_reload()
```

### Development Dashboard

```python
import threading
import time
from datetime import datetime

class HotReloadDashboard:
    """Simple dashboard for monitoring hot-reload activity."""
    
    def __init__(self, config: HotReloadableConfigProvider):
        self.config = config
        self.running = False
        self.stats = {
            'reloads': 0,
            'changes': 0,
            'errors': 0,
            'last_reload': None
        }
        
        # Subscribe to all changes
        config.hot_reload.subscribe("*", self)
    
    def on_config_change(self, path: str, old_value: Any, new_value: Any):
        """Track configuration changes."""
        self.stats['changes'] += 1
        self.stats['last_reload'] = datetime.now()
    
    def on_reload_error(self, error: Exception, changes: List[ConfigChange]):
        """Track reload errors."""
        self.stats['errors'] += 1
    
    def start(self):
        """Start the dashboard."""
        self.running = True
        self.thread = threading.Thread(target=self._run_dashboard)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop the dashboard."""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()
    
    def _run_dashboard(self):
        """Run the dashboard display loop."""
        while self.running:
            self._display_status()
            time.sleep(1)
    
    def _display_status(self):
        """Display current status."""
        # Clear screen (works on Unix-like systems)
        print("\033[2J\033[H", end="")
        
        print("=== Hot-Reload Dashboard ===")
        print(f"Status: {'Enabled' if self.config.hot_reload.is_enabled() else 'Disabled'}")
        
        status = self.config.hot_reload.get_status()
        print(f"Watching: {len(status.watch_paths)} paths")
        print(f"Subscribers: {status.subscriber_count}")
        print(f"Pending changes: {status.pending_changes}")
        
        print("\n=== Statistics ===")
        print(f"Total changes: {self.stats['changes']}")
        print(f"Reload errors: {self.stats['errors']}")
        
        if self.stats['last_reload']:
            elapsed = (datetime.now() - self.stats['last_reload']).total_seconds()
            print(f"Last reload: {elapsed:.0f}s ago")
        
        print("\n=== Version History ===")
        history = self.config.hot_reload.get_version_history(limit=5)
        for version in history:
            print(f"{version.timestamp.strftime('%H:%M:%S')} - "
                  f"{version.id[:8]} ({version.source.value})")
        
        print("\nPress Ctrl+C to exit")

# Usage
config = HotReloadableConfigProvider()
dashboard = HotReloadDashboard(config)

try:
    dashboard.start()
    # Keep the main thread alive
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    dashboard.stop()
    print("\nDashboard stopped")
```

## Troubleshooting

### Common Issues

```python
class HotReloadTroubleshooter:
    """Troubleshoot hot-reload issues."""
    
    def __init__(self, config: HotReloadableConfigProvider):
        self.config = config
    
    def diagnose(self):
        """Run diagnostic checks."""
        print("=== Hot-Reload Diagnostics ===\n")
        
        # Check if enabled
        if not self.config.hot_reload.is_enabled():
            print("❌ Hot-reload is DISABLED")
            print("   - Check environment: " + self.config.get_environment())
            print("   - Enable with: config.hot_reload.enable()")
            return
        
        print("✅ Hot-reload is ENABLED")
        
        # Check watch paths
        paths = self.config.hot_reload.get_watch_paths()
        print(f"\n📁 Watching {len(paths)} paths:")
        for path in paths:
            if path.exists():
                print(f"   ✅ {path}")
            else:
                print(f"   ❌ {path} (does not exist)")
        
        # Check file permissions
        print("\n🔐 File permissions:")
        for path in paths:
            if path.exists():
                if os.access(path, os.R_OK):
                    print(f"   ✅ {path} is readable")
                else:
                    print(f"   ❌ {path} is NOT readable")
        
        # Check recent errors
        status = self.config.hot_reload.get_status()
        if status.error_count > 0:
            print(f"\n⚠️  {status.error_count} errors detected")
        
        # Test reload
        print("\n🔄 Testing reload...")
        result = self.config.hot_reload.reload_now()
        if result.success:
            print(f"   ✅ Reload successful ({result.duration_ms:.1f}ms)")
        else:
            print(f"   ❌ Reload failed: {result.errors}")
    
    def fix_common_issues(self):
        """Provide fixes for common issues."""
        print("\n=== Common Fixes ===")
        
        print("\n1. Hot-reload not detecting changes:")
        print("   - Check file system events are supported")
        print("   - Try touching the config file: touch config/base.yaml")
        print("   - Check for editor safe-write mode (disable it)")
        
        print("\n2. Validation errors on reload:")
        print("   - Check YAML syntax with: yamllint config/")
        print("   - Validate configuration manually")
        print("   - Check for type mismatches")
        
        print("\n3. Performance issues:")
        print("   - Increase debounce time")
        print("   - Reduce number of subscribers")
        print("   - Check for notification loops")

# Usage
config = HotReloadableConfigProvider()
troubleshooter = HotReloadTroubleshooter(config)

# Run diagnostics
troubleshooter.diagnose()

# Show common fixes
troubleshooter.fix_common_issues()
```

### Debug Mode

```python
# Enable debug logging for hot-reload
import logging

# Set up debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("phoenix_real_estate.config.hot_reload")
logger.setLevel(logging.DEBUG)

# Initialize with debug options
config = HotReloadableConfigProvider(
    enable_hot_reload=True,
    hot_reload_options=HotReloadOptions(
        enable_metrics=True,
        enable_audit_log=True,
        debounce_ms=200  # Slower for debugging
    )
)

# Add debug subscriber
class DebugSubscriber(ConfigSubscriber):
    def on_config_change(self, path: str, old_value: Any, new_value: Any):
        print(f"[DEBUG] Change: {path}")
        print(f"        Old: {repr(old_value)}")
        print(f"        New: {repr(new_value)}")
        print(f"        Type: {type(old_value).__name__} → {type(new_value).__name__}")

config.hot_reload.subscribe("*", DebugSubscriber())
```

## Best Practices

1. **Always handle reload errors gracefully** - Don't let configuration errors crash your application
2. **Use specific subscriptions** - Subscribe to specific paths rather than "*" for better performance
3. **Validate critical changes** - Add custom validators for business-critical configuration
4. **Test in development** - Thoroughly test hot-reload behavior before relying on it
5. **Monitor performance** - Watch for excessive reloads or notification loops
6. **Document dependencies** - Clearly document which components depend on which configuration
7. **Use versioning** - Keep configuration version numbers for migration support
8. **Implement circuit breakers** - Prevent reload storms from causing issues