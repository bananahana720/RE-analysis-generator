@echo off
REM Phoenix Real Estate Production Monitoring Startup Script
REM Quick deployment for Windows environments

echo ===============================================================================
echo Phoenix Real Estate - Production Monitoring Infrastructure
echo ===============================================================================
echo.

REM Change to monitoring config directory
cd /d "%~dp0..\..\config\monitoring"

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop first.
    echo.
    pause
    exit /b 1
)

echo ✅ Docker is running
echo.

REM Deploy monitoring infrastructure
echo 🚀 Deploying monitoring infrastructure...
docker compose -f production-docker-compose.yml up -d --remove-orphans

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ Deployment failed. Check Docker logs for details.
    echo.
    pause
    exit /b 1
)

echo.
echo ⏳ Waiting for services to initialize...
timeout /t 30 /nobreak >nul

echo.
echo ===============================================================================
echo 🎉 MONITORING INFRASTRUCTURE DEPLOYED!
echo ===============================================================================
echo.
echo 🎯 EXECUTIVE DASHBOARD
echo    URL: http://localhost:3000/d/phoenix-executive
echo    Purpose: System uptime, cost tracking, success rates
echo.
echo 📊 OPERATIONAL DASHBOARD  
echo    URL: http://localhost:3000/d/phoenix-operational
echo    Purpose: Real-time system health, API performance
echo.
echo ⚡ PERFORMANCE DASHBOARD
echo    URL: http://localhost:3000/d/phoenix-performance  
echo    Purpose: Performance baselines, resource utilization
echo.
echo 💼 BUSINESS INTELLIGENCE DASHBOARD
echo    URL: http://localhost:3000/d/phoenix-business
echo    Purpose: Collection metrics, cost efficiency
echo.
echo 🔧 SYSTEM ACCESS
echo    Grafana:      http://localhost:3000 (admin/phoenix_admin_2024)
echo    Prometheus:   http://localhost:9091
echo    AlertManager: http://localhost:9093
echo.
echo 📈 METRICS ENDPOINTS
echo    Health Check:      http://localhost:8080/health
echo    Cost Summary:      http://localhost:8080/cost-summary
echo    Performance:       http://localhost:8080/performance-summary
echo    Business Metrics:  http://localhost:8080/business-summary
echo.
echo ===============================================================================
echo 🚨 NEXT STEPS FOR PRODUCTION GO-LIVE:
echo ===============================================================================
echo.
echo 1. Open Grafana at http://localhost:3000
echo 2. Login with admin/phoenix_admin_2024
echo 3. Verify all 4 dashboards are displaying data
echo 4. Test alert notifications in AlertManager
echo 5. Validate cost tracking is active
echo 6. Confirm performance baselines are configured
echo.
echo ✅ READY FOR PRODUCTION DEPLOYMENT!
echo.

REM Open browser to Grafana
start http://localhost:3000

echo Press any key to view deployment status...
pause >nul

REM Show container status
echo.
echo 📊 Container Status:
docker compose -f production-docker-compose.yml ps

echo.
echo Press any key to exit...
pause >nul