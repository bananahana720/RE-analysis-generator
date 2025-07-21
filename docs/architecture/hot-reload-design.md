# Hot-Reload Configuration System - Architectural Design

## Overview

This document outlines the architectural design for implementing a hot-reload capability in the Phoenix Real Estate configuration system. The design enables zero-downtime configuration updates during development while maintaining thread safety and data integrity.

## Design Goals

1. **Zero-Downtime Updates**: Configuration changes applied without restarting the application
2. **Development-Only**: Feature automatically disabled in production environments
3. **Thread Safety**: All reload operations are thread-safe and atomic
4. **Minimal Performance Impact**: < 1% CPU overhead when enabled
5. **Validation Before Apply**: All changes validated before being applied
6. **Rollback Capability**: Ability to revert to previous configuration on error
7. **Change Notifications**: Components notified of relevant configuration changes

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Hot-Reload Configuration System              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐ │
│  │ File Watcher │───>│  Validator   │───>│ Version Manager │ │
│  └──────────────┘    └──────────────┘    └─────────────────┘ │
│         │                                          │           │
│         v                                          v           │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐ │
│  │Change Queue  │    │Config Loader │    │  Notification   │ │
│  └──────────────┘    └──────────────┘    │    Service      │ │
│                             │              └─────────────────┘ │
│                             v                      ^           │
│                      ┌──────────────┐             │           │
│                      │Thread-Safe   │             │           │
│                      │Config Store  │─────────────┘           │
│                      └──────────────┘                         │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. File Watcher (`HotReloadWatcher`)
- Monitors configuration files for changes
- Supports YAML, .env, and .env.* files
- Uses efficient OS-level file watching (watchdog library)
- Debounces rapid changes (100ms default)
- Filters out temporary files and editor artifacts

#### 2. Configuration Validator (`ConfigChangeValidator`)
- Validates changed configuration before applying
- Performs schema validation
- Checks type constraints
- Validates business rules
- Returns detailed error messages

#### 3. Version Manager (`ConfigVersionManager`)
- Maintains configuration version history
- Supports rollback to previous versions
- Implements versioning strategy (timestamp-based)
- Limits version history (default: 10 versions)
- Provides diff capabilities between versions

#### 4. Change Queue (`ConfigChangeQueue`)
- Thread-safe queue for configuration changes
- Supports priority changes (e.g., security updates)
- Implements batch processing for efficiency
- Provides change coalescing for rapid updates

#### 5. Configuration Loader (`HotReloadLoader`)
- Loads configuration changes atomically
- Merges changes with existing configuration
- Handles partial updates
- Supports different merge strategies

#### 6. Notification Service (`ConfigChangeNotifier`)
- Implements subscriber pattern
- Notifies components of configuration changes
- Supports filtered subscriptions (by config path)
- Provides both sync and async notifications

#### 7. Thread-Safe Store (`AtomicConfigStore`)
- Thread-safe configuration storage
- Supports atomic reads and writes
- Implements copy-on-write for efficiency
- Provides consistent snapshots

## Implementation Design

### Class Hierarchy

```python
# Base classes
class ConfigReloadable(ABC):
    """Interface for reloadable configuration components"""
    @abstractmethod
    def reload_config(self, changes: Dict[str, Any]) -> None:
        pass

class ConfigSubscriber(ABC):
    """Interface for configuration change subscribers"""
    @abstractmethod
    def on_config_change(self, path: str, old_value: Any, new_value: Any) -> None:
        pass

# Core implementation classes
class HotReloadManager:
    """Main hot-reload orchestrator"""
    def __init__(self, config_provider: ConfigProvider):
        self.enabled = self._is_development()
        self.watcher = HotReloadWatcher()
        self.validator = ConfigChangeValidator()
        self.version_manager = ConfigVersionManager()
        self.change_queue = ConfigChangeQueue()
        self.loader = HotReloadLoader()
        self.notifier = ConfigChangeNotifier()
        self.store = AtomicConfigStore()

class HotReloadWatcher:
    """File system watcher for configuration files"""
    def __init__(self, watch_paths: List[Path]):
        self.observer = Observer()
        self.debouncer = Debouncer(delay_ms=100)

class ConfigVersionManager:
    """Manages configuration versions and rollback"""
    def __init__(self, max_versions: int = 10):
        self.versions: Deque[ConfigVersion] = deque(maxlen=max_versions)
        self.current_version: Optional[ConfigVersion] = None

class ConfigChangeNotifier:
    """Notification service for configuration changes"""
    def __init__(self):
        self.subscribers: Dict[str, List[ConfigSubscriber]] = defaultdict(list)
        self.executor = ThreadPoolExecutor(max_workers=5)
```

### Thread Safety Strategy

1. **Read-Write Locks**: Use `threading.RLock()` for configuration access
2. **Atomic Operations**: All configuration updates are atomic
3. **Copy-on-Write**: Configuration objects are immutable
4. **Thread-Local Storage**: For transaction-like behavior
5. **Lock-Free Reads**: Optimistic concurrency for read operations

### Change Detection Algorithm

```python
def detect_changes(old_config: Dict, new_config: Dict) -> List[ConfigChange]:
    """Detect configuration changes with path tracking"""
    changes = []
    
    def compare_recursive(old, new, path=""):
        # Handle additions
        for key in new:
            current_path = f"{path}.{key}" if path else key
            if key not in old:
                changes.append(ConfigChange(
                    path=current_path,
                    type=ChangeType.ADD,
                    old_value=None,
                    new_value=new[key]
                ))
            elif old[key] != new[key]:
                if isinstance(old[key], dict) and isinstance(new[key], dict):
                    compare_recursive(old[key], new[key], current_path)
                else:
                    changes.append(ConfigChange(
                        path=current_path,
                        type=ChangeType.MODIFY,
                        old_value=old[key],
                        new_value=new[key]
                    ))
        
        # Handle deletions
        for key in old:
            if key not in new:
                current_path = f"{path}.{key}" if path else key
                changes.append(ConfigChange(
                    path=current_path,
                    type=ChangeType.DELETE,
                    old_value=old[key],
                    new_value=None
                ))
    
    compare_recursive(old_config, new_config)
    return changes
```

### Validation Pipeline

```python
class ValidationPipeline:
    """Multi-stage validation pipeline"""
    
    def validate(self, changes: List[ConfigChange]) -> ValidationResult:
        stages = [
            self.validate_syntax,
            self.validate_types,
            self.validate_ranges,
            self.validate_dependencies,
            self.validate_business_rules
        ]
        
        for stage in stages:
            result = stage(changes)
            if not result.is_valid:
                return result
        
        return ValidationResult(is_valid=True)
```

## API Specification

### Core API

```python
# Hot-reload manager API
class HotReloadManager:
    def enable(self) -> None:
        """Enable hot-reload (development only)"""
    
    def disable(self) -> None:
        """Disable hot-reload"""
    
    def is_enabled(self) -> bool:
        """Check if hot-reload is enabled"""
    
    def reload_now(self) -> None:
        """Force immediate configuration reload"""
    
    def rollback(self, version_id: Optional[str] = None) -> None:
        """Rollback to previous version or specific version"""
    
    def get_version_history(self) -> List[ConfigVersion]:
        """Get configuration version history"""
    
    def subscribe(self, path: str, subscriber: ConfigSubscriber) -> SubscriptionHandle:
        """Subscribe to configuration changes"""
    
    def unsubscribe(self, handle: SubscriptionHandle) -> None:
        """Unsubscribe from configuration changes"""

# Configuration provider extensions
class HotReloadableConfigProvider(EnvironmentConfigProvider):
    def __init__(self, *args, enable_hot_reload: bool = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.hot_reload = HotReloadManager(self)
    
    def get_with_reload(self, key: str, default: Any = None) -> Any:
        """Get configuration value with hot-reload support"""
    
    def watch_value(self, key: str, callback: Callable) -> WatchHandle:
        """Watch specific configuration value for changes"""

# Subscriber interface
class ConfigSubscriber(ABC):
    @abstractmethod
    def on_config_change(self, path: str, old_value: Any, new_value: Any) -> None:
        """Handle configuration change notification"""
    
    def on_reload_error(self, error: Exception) -> None:
        """Handle reload error (optional)"""
        pass
```

### Integration API

```python
# Database configuration hot-reload
class HotReloadableDatabaseConfig(ConfigSubscriber):
    def on_config_change(self, path: str, old_value: Any, new_value: Any):
        if path.startswith("database."):
            self.reconnect_pool()

# Logging configuration hot-reload
class HotReloadableLoggingConfig(ConfigSubscriber):
    def on_config_change(self, path: str, old_value: Any, new_value: Any):
        if path == "logging.level":
            logging.getLogger().setLevel(new_value)

# Rate limiter hot-reload
class HotReloadableRateLimiter(ConfigSubscriber):
    def on_config_change(self, path: str, old_value: Any, new_value: Any):
        if path.startswith("collection.rate_limiting."):
            self.update_limits()
```

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
1. Implement `HotReloadWatcher` with basic file monitoring
2. Create `AtomicConfigStore` with thread-safe operations
3. Implement `ConfigChangeValidator` with basic validation
4. Create `ConfigChangeQueue` for change management
5. Write comprehensive unit tests

### Phase 2: Version Management (Week 2)
1. Implement `ConfigVersionManager` with versioning
2. Add rollback capability
3. Create version diff functionality
4. Implement version pruning strategy
5. Add version persistence (optional)

### Phase 3: Notification System (Week 3)
1. Implement `ConfigChangeNotifier` with subscriber pattern
2. Add filtered subscriptions
3. Implement async notification support
4. Create notification batching
5. Add dead-letter queue for failed notifications

### Phase 4: Integration (Week 4)
1. Integrate with existing `EnvironmentConfigProvider`
2. Create `HotReloadableConfigProvider` wrapper
3. Add hot-reload support to major components
4. Implement graceful degradation
5. Add comprehensive integration tests

### Phase 5: Production Readiness (Week 5)
1. Add performance monitoring
2. Implement circuit breaker for reload failures
3. Add comprehensive logging and metrics
4. Create developer documentation
5. Perform load testing and optimization

## Performance Considerations

### Resource Usage
- **Memory**: ~1MB base + 100KB per version stored
- **CPU**: < 1% overhead during normal operation
- **File Handles**: 1 per watched directory
- **Threads**: 2-5 background threads

### Optimization Strategies
1. **Debouncing**: Prevent rapid reloads (100ms default)
2. **Batch Processing**: Group multiple changes
3. **Lazy Loading**: Only reload affected components
4. **Caching**: Cache parsed configuration
5. **Lock-Free Reads**: Use RCU pattern for reads

## Security Considerations

1. **Development Only**: Automatically disabled in production
2. **Path Validation**: Prevent directory traversal attacks
3. **Permission Checks**: Verify file permissions before reading
4. **Sanitization**: Sanitize configuration values
5. **Audit Logging**: Log all configuration changes

## Example Usage Patterns

### Basic Usage
```python
# Initialize with hot-reload
config = HotReloadableConfigProvider(enable_hot_reload=True)

# Subscribe to changes
class MyComponent(ConfigSubscriber):
    def on_config_change(self, path, old_value, new_value):
        if path == "api.timeout":
            self.update_timeout(new_value)

component = MyComponent()
config.hot_reload.subscribe("api.timeout", component)
```

### Advanced Usage
```python
# Watch specific value
handle = config.watch_value("database.pool_size", lambda new_size: 
    print(f"Pool size changed to {new_size}")
)

# Force reload
config.hot_reload.reload_now()

# Check version history
versions = config.hot_reload.get_version_history()
for version in versions:
    print(f"Version {version.id}: {version.timestamp}")

# Rollback on error
try:
    # Some operation that depends on config
    risky_operation()
except Exception as e:
    config.hot_reload.rollback()
    logger.error(f"Rolled back config due to: {e}")
```

### Component Integration
```python
# Database component with hot-reload
class DatabaseManager(ConfigSubscriber):
    def __init__(self, config: HotReloadableConfigProvider):
        self.config = config
        config.hot_reload.subscribe("database", self)
        self.setup_connection()
    
    def on_config_change(self, path, old_value, new_value):
        if path.startswith("database."):
            logger.info(f"Database config changed: {path}")
            self.reconnect()
    
    def reconnect(self):
        # Gracefully close existing connections
        self.close_connections()
        # Establish new connections with updated config
        self.setup_connection()
```

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock file system operations
- Test thread safety with concurrent access
- Verify validation logic
- Test error handling and rollback

### Integration Tests
- Test full hot-reload cycle
- Verify subscriber notifications
- Test configuration persistence
- Verify production disable
- Test performance under load

### Example Test
```python
def test_hot_reload_cycle():
    """Test complete hot-reload cycle"""
    config = HotReloadableConfigProvider(enable_hot_reload=True)
    
    # Subscribe to changes
    changes_received = []
    config.hot_reload.subscribe("test.value", 
        lambda p, o, n: changes_received.append((p, o, n))
    )
    
    # Modify config file
    with open("config/development.yaml", "a") as f:
        f.write("\ntest:\n  value: 42\n")
    
    # Wait for reload
    time.sleep(0.2)
    
    # Verify change was detected and applied
    assert config.get("test.value") == 42
    assert len(changes_received) == 1
    assert changes_received[0] == ("test.value", None, 42)
```

## Conclusion

This hot-reload configuration system provides a robust, thread-safe solution for zero-downtime configuration updates during development. The design prioritizes safety, performance, and developer experience while maintaining compatibility with the existing configuration system.