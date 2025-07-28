@echo off
:: MongoDB Service Starter for Phoenix Real Estate Project
:: Run this script as Administrator

echo ============================================
echo MongoDB Service Setup
echo ============================================
echo.

:: Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script requires Administrator privileges!
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

:: Set MongoDB paths
set MONGO_BIN=C:\Program Files\MongoDB\Server\8.1\bin
set DATA_PATH=C:\data\db
set LOG_PATH=C:\data\log

:: Create directories
echo Creating data directories...
if not exist "%DATA_PATH%" mkdir "%DATA_PATH%"
if not exist "%LOG_PATH%" mkdir "%LOG_PATH%"
echo [OK] Directories created

:: Check if MongoDB service exists
sc query MongoDB >nul 2>&1
if %errorlevel% == 0 (
    echo.
    echo MongoDB service already exists.
    :: Check if it's running
    sc query MongoDB | find "RUNNING" >nul
    if %errorlevel% == 0 (
        echo [OK] MongoDB is already running!
    ) else (
        echo Starting MongoDB service...
        net start MongoDB
        if %errorlevel% == 0 (
            echo [OK] MongoDB service started successfully!
        ) else (
            echo [ERROR] Failed to start MongoDB service
            echo Trying to reinstall service...
            "%MONGO_BIN%\mongod.exe" --remove >nul 2>&1
            goto :install_service
        )
    )
) else (
    :install_service
    echo.
    echo Installing MongoDB service...
    "%MONGO_BIN%\mongod.exe" --dbpath="%DATA_PATH%" --logpath="%LOG_PATH%\mongod.log" --install --serviceName "MongoDB" --serviceDisplayName "MongoDB" --serviceDescription "MongoDB Database Server"
    
    if %errorlevel% == 0 (
        echo [OK] MongoDB service installed
        echo.
        echo Starting MongoDB service...
        net start MongoDB
        if %errorlevel% == 0 (
            echo [OK] MongoDB service started successfully!
        ) else (
            echo [ERROR] Failed to start MongoDB service
        )
    ) else (
        echo [ERROR] Failed to install MongoDB service
    )
)

echo.
echo ============================================
echo MongoDB Status:
echo ============================================
echo Connection: mongodb://localhost:27017
echo Data Path: %DATA_PATH%
echo Log Path: %LOG_PATH%\mongod.log
echo.
echo Commands:
echo - Stop MongoDB:  net stop MongoDB
echo - Start MongoDB: net start MongoDB
echo - Remove service: "%MONGO_BIN%\mongod.exe" --remove
echo ============================================
echo.
pause