# Hot-Reload Configuration API Specification

## Table of Contents
1. [Core API](#core-api)
2. [Configuration Provider API](#configuration-provider-api)
3. [Subscriber API](#subscriber-api)
4. [Version Management API](#version-management-api)
5. [Notification API](#notification-api)
6. [Error Handling](#error-handling)
7. [Type Definitions](#type-definitions)

## Core API

### HotReloadManager

The main orchestrator for hot-reload functionality.

```python
class HotReloadManager:
    """
    Manages hot-reload functionality for configuration files.
    
    This class coordinates file watching, validation, versioning,
    and notification of configuration changes.
    """
    
    def __init__(
        self,
        config_provider: ConfigProvider,
        watch_paths: Optional[List[Path]] = None,
        enable: Optional[bool] = None,
        debounce_ms: int = 100,
        max_versions: int = 10
    ):
        """
        Initialize the hot-reload manager.
        
        Args:
            config_provider: The configuration provider to manage
            watch_paths: Paths to watch for changes (auto-detected if None)
            enable: Enable hot-reload (auto-detected from environment if None)
            debounce_ms: Milliseconds to wait before processing changes
            max_versions: Maximum number of versions to keep in history
        """
    
    def enable(self) -> None:
        """
        Enable hot-reload functionality.
        
        Raises:
            RuntimeError: If called in production environment
        """
    
    def disable(self) -> None:
        """
        Disable hot-reload functionality.
        
        Stops file watching and clears pending changes.
        """
    
    def is_enabled(self) -> bool:
        """
        Check if hot-reload is currently enabled.
        
        Returns:
            True if hot-reload is enabled, False otherwise
        """
    
    def reload_now(self, force: bool = False) -> ReloadResult:
        """
        Force immediate configuration reload.
        
        Args:
            force: Skip validation if True (dangerous!)
            
        Returns:
            ReloadResult with status and any errors
        """
    
    def rollback(
        self,
        version_id: Optional[str] = None,
        steps: int = 1
    ) -> RollbackResult:
        """
        Rollback configuration to a previous version.
        
        Args:
            version_id: Specific version ID to rollback to
            steps: Number of versions to rollback (if version_id not provided)
            
        Returns:
            RollbackResult with status and rolled back version
            
        Raises:
            VersionNotFoundError: If specified version doesn't exist
        """
    
    def get_status(self) -> HotReloadStatus:
        """
        Get current hot-reload status.
        
        Returns:
            HotReloadStatus with detailed information
        """
    
    def add_watch_path(self, path: Path) -> None:
        """
        Add a new path to watch for configuration changes.
        
        Args:
            path: Path to watch (file or directory)
            
        Raises:
            ValueError: If path doesn't exist
        """
    
    def remove_watch_path(self, path: Path) -> None:
        """
        Remove a path from configuration watching.
        
        Args:
            path: Path to stop watching
        """
    
    def get_watch_paths(self) -> List[Path]:
        """
        Get list of currently watched paths.
        
        Returns:
            List of paths being watched
        """
```

## Configuration Provider API

### HotReloadableConfigProvider

Extended configuration provider with hot-reload support.

```python
class HotReloadableConfigProvider(EnvironmentConfigProvider):
    """
    Configuration provider with hot-reload capabilities.
    
    Extends the base configuration provider with automatic
    reload support and change notifications.
    """
    
    def __init__(
        self,
        config_dir: Optional[Union[str, Path]] = None,
        environment: Optional[str] = None,
        load_dotenv: bool = True,
        enable_hot_reload: Optional[bool] = None,
        hot_reload_options: Optional[HotReloadOptions] = None
    ):
        """
        Initialize configuration provider with hot-reload support.
        
        Args:
            config_dir: Configuration directory
            environment: Environment name
            load_dotenv: Whether to load .env files
            enable_hot_reload: Enable hot-reload (auto-detect if None)
            hot_reload_options: Advanced hot-reload configuration
        """
    
    @property
    def hot_reload(self) -> HotReloadManager:
        """Access the hot-reload manager."""
    
    def get_with_reload(
        self,
        key: str,
        default: Optional[Any] = None,
        timeout: float = 0.1
    ) -> Any:
        """
        Get configuration value, checking for pending reloads.
        
        Args:
            key: Configuration key
            default: Default value if not found
            timeout: Max seconds to wait for pending reload
            
        Returns:
            Configuration value
        """
    
    def watch_value(
        self,
        key: str,
        callback: Callable[[str, Any, Any], None],
        immediate: bool = True
    ) -> WatchHandle:
        """
        Watch a specific configuration value for changes.
        
        Args:
            key: Configuration key to watch
            callback: Function called on changes (key, old_value, new_value)
            immediate: Call callback immediately with current value
            
        Returns:
            WatchHandle for unsubscribing
        """
    
    def watch_pattern(
        self,
        pattern: str,
        callback: Callable[[str, Any, Any], None]
    ) -> WatchHandle:
        """
        Watch configuration keys matching a pattern.
        
        Args:
            pattern: Glob pattern for keys (e.g., "database.*")
            callback: Function called on changes
            
        Returns:
            WatchHandle for unsubscribing
        """
    
    def unwatch(self, handle: WatchHandle) -> None:
        """
        Stop watching a configuration value or pattern.
        
        Args:
            handle: Watch handle returned by watch_value/watch_pattern
        """
    
    def refresh(self) -> None:
        """
        Manually refresh configuration from disk.
        
        Useful for programmatic configuration updates.
        """
```

## Subscriber API

### ConfigSubscriber

Interface for components that need configuration change notifications.

```python
class ConfigSubscriber(ABC):
    """
    Abstract base class for configuration change subscribers.
    
    Implement this interface to receive notifications about
    configuration changes.
    """
    
    @abstractmethod
    def on_config_change(
        self,
        path: str,
        old_value: Any,
        new_value: Any
    ) -> None:
        """
        Handle configuration change notification.
        
        Args:
            path: Configuration key path that changed
            old_value: Previous value (None if newly added)
            new_value: New value (None if deleted)
        """
    
    def on_config_reload(
        self,
        changes: List[ConfigChange]
    ) -> None:
        """
        Handle bulk configuration reload.
        
        Called when multiple configuration values change at once.
        Default implementation calls on_config_change for each change.
        
        Args:
            changes: List of all configuration changes
        """
        for change in changes:
            self.on_config_change(
                change.path,
                change.old_value,
                change.new_value
            )
    
    def on_reload_error(
        self,
        error: Exception,
        changes: List[ConfigChange]
    ) -> None:
        """
        Handle configuration reload error.
        
        Called when configuration reload fails validation or
        encounters an error during application.
        
        Args:
            error: The exception that occurred
            changes: Changes that were attempted
        """
        pass
    
    def on_rollback(
        self,
        from_version: ConfigVersion,
        to_version: ConfigVersion
    ) -> None:
        """
        Handle configuration rollback notification.
        
        Args:
            from_version: Version being rolled back from
            to_version: Version being rolled back to
        """
        pass
```

### Subscription Management

```python
class SubscriptionManager:
    """Manages configuration change subscriptions."""
    
    def subscribe(
        self,
        pattern: str,
        subscriber: ConfigSubscriber,
        priority: Priority = Priority.NORMAL
    ) -> SubscriptionHandle:
        """
        Subscribe to configuration changes.
        
        Args:
            pattern: Path pattern to subscribe to (supports wildcards)
            subscriber: Subscriber instance
            priority: Notification priority
            
        Returns:
            Handle for unsubscribing
        """
    
    def unsubscribe(self, handle: SubscriptionHandle) -> None:
        """Unsubscribe from configuration changes."""
    
    def unsubscribe_all(self, subscriber: ConfigSubscriber) -> int:
        """
        Remove all subscriptions for a subscriber.
        
        Returns:
            Number of subscriptions removed
        """
```

## Version Management API

### ConfigVersionManager

Manages configuration versions and history.

```python
class ConfigVersionManager:
    """
    Manages configuration versions for rollback capability.
    """
    
    def create_version(
        self,
        config: Dict[str, Any],
        source: VersionSource = VersionSource.FILE_CHANGE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConfigVersion:
        """
        Create a new configuration version.
        
        Args:
            config: Configuration snapshot
            source: Source of the version
            metadata: Additional metadata
            
        Returns:
            Created version
        """
    
    def get_current_version(self) -> Optional[ConfigVersion]:
        """Get the current configuration version."""
    
    def get_version(self, version_id: str) -> ConfigVersion:
        """
        Get a specific version by ID.
        
        Raises:
            VersionNotFoundError: If version doesn't exist
        """
    
    def get_version_history(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> List[ConfigVersion]:
        """Get configuration version history."""
    
    def diff_versions(
        self,
        version_a: str,
        version_b: str
    ) -> VersionDiff:
        """
        Compare two configuration versions.
        
        Returns:
            VersionDiff with changes between versions
        """
    
    def prune_old_versions(
        self,
        keep_count: int = 10,
        keep_days: Optional[int] = None
    ) -> int:
        """
        Remove old configuration versions.
        
        Returns:
            Number of versions removed
        """
```

## Notification API

### ConfigChangeNotifier

Handles notification of configuration changes.

```python
class ConfigChangeNotifier:
    """
    Manages notification of configuration changes to subscribers.
    """
    
    def notify_change(
        self,
        change: ConfigChange,
        sync: bool = False
    ) -> NotificationResult:
        """
        Notify subscribers of a configuration change.
        
        Args:
            change: The configuration change
            sync: Execute notifications synchronously
            
        Returns:
            Result with success/failure counts
        """
    
    def notify_batch(
        self,
        changes: List[ConfigChange],
        sync: bool = False
    ) -> NotificationResult:
        """
        Notify subscribers of multiple changes.
        
        Args:
            changes: List of configuration changes
            sync: Execute notifications synchronously
            
        Returns:
            Result with success/failure counts
        """
    
    def set_notification_timeout(self, timeout: float) -> None:
        """Set timeout for subscriber notifications."""
    
    def set_error_handler(
        self,
        handler: Callable[[Exception, ConfigSubscriber], None]
    ) -> None:
        """Set custom error handler for notification failures."""
```

## Error Handling

### Exception Classes

```python
class HotReloadError(Exception):
    """Base exception for hot-reload errors."""
    pass

class ReloadValidationError(HotReloadError):
    """Configuration validation failed during reload."""
    def __init__(
        self,
        message: str,
        validation_errors: List[ValidationError]
    ):
        self.validation_errors = validation_errors

class VersionNotFoundError(HotReloadError):
    """Requested configuration version not found."""
    pass

class RollbackError(HotReloadError):
    """Configuration rollback failed."""
    pass

class WatcherError(HotReloadError):
    """File watcher encountered an error."""
    pass

class SubscriberError(HotReloadError):
    """Subscriber notification failed."""
    def __init__(
        self,
        message: str,
        subscriber: ConfigSubscriber,
        original_error: Exception
    ):
        self.subscriber = subscriber
        self.original_error = original_error
```

## Type Definitions

### Core Types

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path

class ChangeType(Enum):
    """Type of configuration change."""
    ADD = "add"
    MODIFY = "modify"
    DELETE = "delete"

class Priority(Enum):
    """Notification priority levels."""
    HIGH = 1
    NORMAL = 2
    LOW = 3

class VersionSource(Enum):
    """Source of configuration version."""
    FILE_CHANGE = "file_change"
    API_UPDATE = "api_update"
    ROLLBACK = "rollback"
    MANUAL = "manual"

@dataclass
class ConfigChange:
    """Represents a single configuration change."""
    path: str
    type: ChangeType
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ConfigVersion:
    """Represents a configuration version."""
    id: str
    timestamp: datetime
    config: Dict[str, Any]
    source: VersionSource
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None

@dataclass
class VersionDiff:
    """Difference between two configuration versions."""
    from_version: ConfigVersion
    to_version: ConfigVersion
    changes: List[ConfigChange]
    summary: str

@dataclass
class ReloadResult:
    """Result of a configuration reload operation."""
    success: bool
    version: Optional[ConfigVersion]
    changes: List[ConfigChange]
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

@dataclass
class RollbackResult:
    """Result of a configuration rollback operation."""
    success: bool
    from_version: ConfigVersion
    to_version: ConfigVersion
    changes: List[ConfigChange]
    errors: List[str] = field(default_factory=list)

@dataclass
class HotReloadStatus:
    """Current status of hot-reload system."""
    enabled: bool
    watching: bool
    watch_paths: List[Path]
    current_version: Optional[ConfigVersion]
    pending_changes: int
    last_reload: Optional[datetime]
    error_count: int
    subscriber_count: int

@dataclass
class HotReloadOptions:
    """Advanced hot-reload configuration options."""
    debounce_ms: int = 100
    max_versions: int = 10
    validate_on_reload: bool = True
    notification_timeout: float = 5.0
    max_subscribers: int = 100
    enable_metrics: bool = False
    enable_audit_log: bool = False

@dataclass
class ValidationError:
    """Configuration validation error details."""
    path: str
    message: str
    constraint: str
    actual_value: Any

@dataclass
class NotificationResult:
    """Result of subscriber notifications."""
    total: int
    success: int
    failed: int
    errors: List[SubscriberError] = field(default_factory=list)

# Handle types
class WatchHandle:
    """Handle for unsubscribing from configuration watches."""
    def __init__(self, id: str, manager: 'SubscriptionManager'):
        self._id = id
        self._manager = manager
    
    def unsubscribe(self) -> None:
        """Unsubscribe this watch."""
        self._manager.unsubscribe(self)

class SubscriptionHandle:
    """Handle for managing subscriptions."""
    def __init__(self, id: str, pattern: str, subscriber: ConfigSubscriber):
        self.id = id
        self.pattern = pattern
        self.subscriber = subscriber
```

### Callback Types

```python
from typing import Callable

# Value change callback
ValueChangeCallback = Callable[[str, Any, Any], None]

# Batch change callback
BatchChangeCallback = Callable[[List[ConfigChange]], None]

# Error handler callback
ErrorHandlerCallback = Callable[[Exception, ConfigSubscriber], None]

# Validation callback
ValidationCallback = Callable[[Dict[str, Any]], List[ValidationError]]
```

## Usage Examples

### Basic Hot-Reload Setup

```python
# Initialize with hot-reload
config = HotReloadableConfigProvider(
    enable_hot_reload=True,
    hot_reload_options=HotReloadOptions(
        debounce_ms=200,
        max_versions=20,
        enable_metrics=True
    )
)

# Check status
status = config.hot_reload.get_status()
print(f"Hot-reload enabled: {status.enabled}")
print(f"Watching {len(status.watch_paths)} paths")
```

### Component Integration

```python
class DatabasePool(ConfigSubscriber):
    """Database connection pool with hot-reload support."""
    
    def __init__(self, config: HotReloadableConfigProvider):
        self.config = config
        self.pool = None
        
        # Subscribe to database configuration changes
        config.hot_reload.subscribe("database.*", self)
        
        # Watch specific values
        self.pool_size_handle = config.watch_value(
            "database.pool_size",
            self._on_pool_size_change
        )
        
        self._initialize_pool()
    
    def on_config_change(self, path: str, old_value: Any, new_value: Any):
        """Handle any database configuration change."""
        logger.info(f"Database config changed: {path}")
        
        if path == "database.uri":
            # Critical change - recreate pool
            self._recreate_pool()
        elif path.startswith("database.pool"):
            # Pool configuration - adjust pool
            self._adjust_pool()
    
    def _on_pool_size_change(self, key: str, old_size: int, new_size: int):
        """Handle pool size changes specifically."""
        logger.info(f"Adjusting pool size from {old_size} to {new_size}")
        self.pool.resize(new_size)
    
    def on_reload_error(self, error: Exception, changes: List[ConfigChange]):
        """Handle reload errors gracefully."""
        logger.error(f"Config reload failed: {error}")
        # Keep using current configuration
    
    def cleanup(self):
        """Cleanup resources and unsubscribe."""
        self.config.unwatch(self.pool_size_handle)
        if self.pool:
            self.pool.close()
```

### Advanced Version Management

```python
# Get version history
history = config.hot_reload.get_version_history()
for version in history:
    print(f"{version.timestamp}: {version.id} ({version.source.value})")

# Compare versions
if len(history) >= 2:
    diff = config.hot_reload.version_manager.diff_versions(
        history[0].id,
        history[1].id
    )
    print(f"Changes between versions: {len(diff.changes)}")
    for change in diff.changes:
        print(f"  {change.type.value} {change.path}: "
              f"{change.old_value} → {change.new_value}")

# Rollback with validation
try:
    result = config.hot_reload.rollback(steps=1)
    if result.success:
        print(f"Rolled back to version {result.to_version.id}")
    else:
        print(f"Rollback failed: {result.errors}")
except VersionNotFoundError:
    print("No previous version available")
```

### Custom Validation

```python
def custom_validator(config: Dict[str, Any]) -> List[ValidationError]:
    """Custom validation logic."""
    errors = []
    
    # Validate database connections
    if config.get("database", {}).get("pool_size", 0) > 100:
        errors.append(ValidationError(
            path="database.pool_size",
            message="Pool size too large for development",
            constraint="<= 100",
            actual_value=config["database"]["pool_size"]
        ))
    
    return errors

# Add custom validator
config.hot_reload.add_validator(custom_validator)
```

This API specification provides a comprehensive interface for the hot-reload configuration system, balancing flexibility with safety and ease of use.