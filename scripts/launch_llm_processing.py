#!/usr/bin/env python
"""
Launch script for LLM Processing Service with comprehensive validation.

This script ensures all dependencies are running and healthy before starting
the LLM processing service.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx
import psutil
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from phoenix_real_estate.foundation import EnvironmentConfigProvider, get_logger
from phoenix_real_estate.foundation.database import DatabaseConnection

console = Console()
logger = get_logger(__name__)


class ServiceValidator:
    """Validates required services are running and healthy."""
    
    def __init__(self):
        self.config = EnvironmentConfigProvider()
        self.services_status: Dict[str, Dict[str, any]] = {}
        
    async def check_mongodb(self) -> Tuple[bool, str]:
        """Check MongoDB connection and health."""
        try:
            client = DatabaseConnection(self.config)
            await client.connect()
            await client.health_check()
            await client.close()
            return True, "Connected and healthy"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    async def check_ollama(self) -> Tuple[bool, str]:
        """Check Ollama service health."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:11434/api/tags", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    llama_models = [m for m in models if "llama3.2" in m.get("name", "")]
                    if llama_models:
                        return True, f"Running with {len(llama_models)} llama3.2 model(s)"
                    else:
                        return False, "No llama3.2 models found"
                else:
                    return False, f"API returned status {response.status_code}"
        except Exception as e:
            return False, f"Service not accessible: {str(e)}"
    
    def check_port_availability(self, port: int) -> Tuple[bool, str]:
        """Check if a port is available for binding."""
        import socket
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    # Port is in use
                    # Try to identify the process
                    for conn in psutil.net_connections():
                        if conn.laddr.port == port and conn.status == 'LISTEN':
                            try:
                                proc = psutil.Process(conn.pid)
                                return False, f"Port in use by {proc.name()} (PID: {conn.pid})"
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                    return False, "Port already in use"
                else:
                    return True, "Port available"
        except Exception as e:
            return False, f"Error checking port: {str(e)}"
    
    def check_disk_space(self, min_gb: float = 5.0) -> Tuple[bool, str]:
        """Check available disk space."""
        try:
            usage = psutil.disk_usage('/')
            available_gb = usage.free / (1024 ** 3)
            percent_used = usage.percent
            
            if available_gb < min_gb:
                return False, f"Only {available_gb:.1f}GB available (need {min_gb}GB)"
            else:
                return True, f"{available_gb:.1f}GB available ({percent_used:.1f}% used)"
        except Exception as e:
            return False, f"Error checking disk: {str(e)}"
    
    def check_memory(self, min_gb: float = 4.0) -> Tuple[bool, str]:
        """Check available system memory."""
        try:
            mem = psutil.virtual_memory()
            available_gb = mem.available / (1024 ** 3)
            percent_used = mem.percent
            
            if available_gb < min_gb:
                return False, f"Only {available_gb:.1f}GB available (need {min_gb}GB)"
            else:
                return True, f"{available_gb:.1f}GB available ({percent_used:.1f}% used)"
        except Exception as e:
            return False, f"Error checking memory: {str(e)}"
    
    async def validate_all(self) -> bool:
        """Run all validation checks."""
        console.print("\n[bold blue]🔍 Validating System Requirements[/bold blue]\n")
        
        checks = [
            ("System Memory", lambda: self.check_memory()),
            ("Disk Space", lambda: self.check_disk_space()),
            ("MongoDB Service", self.check_mongodb),
            ("Ollama Service", self.check_ollama),
            ("Port 8080 (API)", lambda: self.check_port_availability(8080)),
            ("Port 9090 (Prometheus)", lambda: self.check_port_availability(9090)),
        ]
        
        table = Table(title="Service Status", show_header=True, header_style="bold magenta")
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        
        all_passed = True
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for name, check_func in checks:
                task = progress.add_task(f"Checking {name}...", total=1)
                
                # Run sync or async function
                if asyncio.iscoroutinefunction(check_func):
                    success, message = await check_func()
                else:
                    success, message = check_func()
                
                progress.update(task, completed=1)
                
                status_icon = "✅" if success else "❌"
                status_color = "green" if success else "red"
                
                table.add_row(
                    name,
                    f"[{status_color}]{status_icon}[/{status_color}]",
                    message
                )
                
                self.services_status[name] = {
                    "success": success,
                    "message": message
                }
                
                if not success:
                    all_passed = False
        
        console.print(table)
        return all_passed


class ServiceLauncher:
    """Launches and manages the LLM processing service."""
    
    def __init__(self):
        self.config = EnvironmentConfigProvider()
        self.process: Optional[subprocess.Popen] = None
        
    def start_service(self) -> bool:
        """Start the LLM processing service."""
        try:
            # Build command
            cmd = [
                sys.executable,
                "-m",
                "phoenix_real_estate.collectors.processing.service"
            ]
            
            # Set environment
            env = dict(os.environ)
            env["PYTHONUNBUFFERED"] = "1"
            
            # Start process
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if it's still running
            if self.process.poll() is None:
                return True
            else:
                # Process exited, get error
                _, stderr = self.process.communicate()
                console.print(f"[red]Service failed to start:[/red]\n{stderr}")
                return False
                
        except Exception as e:
            console.print(f"[red]Failed to start service: {e}[/red]")
            return False
    
    async def wait_for_health(self, timeout: int = 30) -> bool:
        """Wait for service to become healthy."""
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get("http://localhost:8080/health")
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "healthy":
                            return True
                except Exception:
                    pass
                
                await asyncio.sleep(1)
        
        return False
    
    def stop_service(self):
        """Stop the service if running."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)


async def main():
    """Main launch sequence."""
    console.print(Panel.fit(
        "[bold cyan]Phoenix Real Estate LLM Processing Service Launcher[/bold cyan]",
        border_style="blue"
    ))
    
    # Step 1: Validate prerequisites
    validator = ServiceValidator()
    if not await validator.validate_all():
        console.print("\n[bold red]❌ Validation Failed![/bold red]")
        console.print("\nPlease fix the issues above and try again.")
        
        # Provide helpful commands
        console.print("\n[yellow]Helpful commands:[/yellow]")
        for service, status in validator.services_status.items():
            if not status["success"]:
                if "MongoDB" in service:
                    console.print("  • Start MongoDB: [cyan]net start MongoDB[/cyan] (run as Administrator)")
                elif "Ollama" in service:
                    console.print("  • Start Ollama: [cyan]ollama serve[/cyan]")
                    console.print("  • Pull model: [cyan]ollama pull llama3.2:latest[/cyan]")
                elif "Port" in service:
                    port = service.split()[1]
                    console.print(f"  • Check port {port}: [cyan]netstat -ano | findstr :{port}[/cyan]")
        
        return 1
    
    console.print("\n[bold green]✅ All validations passed![/bold green]\n")
    
    # Step 2: Start the service
    launcher = ServiceLauncher()
    
    with console.status("[bold green]Starting LLM Processing Service...[/bold green]"):
        if not launcher.start_service():
            console.print("[bold red]❌ Failed to start service[/bold red]")
            return 1
    
    # Step 3: Wait for health check
    with console.status("[bold green]Waiting for service to become healthy...[/bold green]"):
        if not await launcher.wait_for_health():
            console.print("[bold red]❌ Service failed health check[/bold red]")
            launcher.stop_service()
            return 1
    
    # Step 4: Display success and monitoring info
    console.print("\n[bold green]🚀 LLM Processing Service Started Successfully![/bold green]\n")
    
    # Create monitoring info table
    info_table = Table(title="Service Information", show_header=False)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="green")
    
    info_table.add_row("Health Check", "http://localhost:8080/health")
    info_table.add_row("LLM Health", "http://localhost:8080/health/llm")
    info_table.add_row("Metrics", "http://localhost:8080/metrics")
    info_table.add_row("Process Endpoint", "http://localhost:8080/process")
    info_table.add_row("Prometheus", "http://localhost:9090")
    info_table.add_row("Grafana", "http://localhost:3000")
    
    console.print(info_table)
    
    console.print("\n[yellow]Press Ctrl+C to stop the service[/yellow]\n")
    
    # Keep running and monitor
    try:
        while True:
            if launcher.process and launcher.process.poll() is not None:
                console.print("\n[bold red]⚠️  Service stopped unexpectedly![/bold red]")
                break
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping service...[/yellow]")
        launcher.stop_service()
        console.print("[green]Service stopped gracefully[/green]")
    
    return 0


if __name__ == "__main__":
    import os
    sys.exit(asyncio.run(main()))