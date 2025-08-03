#!/usr/bin/env python
"""
Quick status check script for LLM Processing Service.

Provides a comprehensive view of the system health and performance metrics.
"""

import asyncio
import sys
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout

console = Console()


class StatusChecker:
    """Checks and displays status of LLM processing system."""

    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.prometheus_url = "http://localhost:9090"

    async def fetch_health(self) -> Optional[Dict[str, Any]]:
        """Fetch health status from the service."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health/llm", timeout=5.0)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            console.print(f"[red]Error fetching health data: {e}[/red]")
        return None

    async def fetch_metrics(self) -> Optional[str]:
        """Fetch raw metrics from the service."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/metrics", timeout=5.0)
                if response.status_code == 200:
                    return response.text
        except Exception:
            pass
        return None

    def parse_metrics(self, metrics_text: str) -> Dict[str, Any]:
        """Parse Prometheus metrics text format."""
        metrics = {}

        for line in metrics_text.split("\n"):
            if line.startswith("#") or not line.strip():
                continue

            try:
                # Parse metric line
                if " " in line:
                    metric_part, value = line.rsplit(" ", 1)

                    # Extract metric name and labels
                    if "{" in metric_part:
                        name, labels_part = metric_part.split("{", 1)
                        labels_part = labels_part.rstrip("}")

                        # Parse labels
                        labels = {}
                        for label in labels_part.split(","):
                            if "=" in label:
                                k, v = label.split("=", 1)
                                labels[k] = v.strip('"')

                        # Store with labels
                        if name not in metrics:
                            metrics[name] = []
                        metrics[name].append({"labels": labels, "value": float(value)})
                    else:
                        metrics[metric_part] = float(value)
            except (ValueError, TypeError):
                continue

        return metrics

    def create_status_table(self, health_data: Dict[str, Any]) -> Table:
        """Create a status table from health data."""
        table = Table(title="System Status", show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")

        # Overall status
        overall_status = health_data.get("status", "unknown")
        status_color = {"healthy": "green", "degraded": "yellow", "unhealthy": "red"}.get(
            overall_status, "white"
        )

        status_icon = {"healthy": "✅", "degraded": "⚠️ ", "unhealthy": "❌"}.get(
            overall_status, "❓"
        )

        table.add_row(
            "Overall Health",
            f"[{status_color}]{status_icon} {overall_status.upper()}[/{status_color}]",
            f"Score: {health_data.get('health_score', 0):.1%}",
        )

        # Component status
        components = health_data.get("components", {})

        for comp_name, comp_data in components.items():
            if isinstance(comp_data, dict):
                comp_status = comp_data.get("status", "unknown")

                # Determine icon and color
                if comp_status == "healthy":
                    icon, color = "✅", "green"
                elif comp_status in ["warning", "degraded"]:
                    icon, color = "⚠️ ", "yellow"
                elif comp_status in ["unhealthy", "critical", "error"]:
                    icon, color = "❌", "red"
                else:
                    icon, color = "❓", "white"

                # Build details
                details = []
                if "response_time_ms" in comp_data:
                    details.append(f"{comp_data['response_time_ms']:.1f}ms")
                if "error" in comp_data:
                    details.append(f"Error: {comp_data['error'][:50]}...")
                if "utilization_percent" in comp_data:
                    details.append(f"{comp_data['utilization_percent']:.1f}% used")

                table.add_row(
                    comp_name.replace("_", " ").title(),
                    f"[{color}]{icon}[/{color}]",
                    " | ".join(details) if details else "-",
                )

        # Uptime
        uptime = health_data.get("uptime", {})
        if uptime:
            table.add_row("Uptime", "[green]🕐[/green]", uptime.get("uptime_human", "N/A"))

        return table

    def create_metrics_table(self, metrics: Dict[str, Any]) -> Table:
        """Create a metrics table from parsed metrics."""
        table = Table(title="Performance Metrics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", justify="right", style="green")

        # Processing metrics
        if "llm_processing_requests_total" in metrics:
            total_requests = sum(m["value"] for m in metrics["llm_processing_requests_total"])
            success_requests = sum(
                m["value"]
                for m in metrics["llm_processing_requests_total"]
                if m["labels"].get("status") == "success"
            )
            error_requests = sum(
                m["value"]
                for m in metrics["llm_processing_requests_total"]
                if m["labels"].get("status") == "error"
            )

            table.add_row("Total Requests", f"{int(total_requests):,}")
            table.add_row("Successful", f"{int(success_requests):,}")
            table.add_row("Errors", f"{int(error_requests):,}")

            if total_requests > 0:
                success_rate = (success_requests / total_requests) * 100
                table.add_row("Success Rate", f"{success_rate:.1f}%")

        # Queue metrics
        if "llm_processing_queue_size" in metrics:
            queue_size = int(metrics["llm_processing_queue_size"])
            table.add_row("Queue Size", str(queue_size))

        # Memory metrics
        if "llm_memory_usage_bytes" in metrics:
            memory_mb = metrics["llm_memory_usage_bytes"] / 1024 / 1024
            table.add_row("Memory Usage", f"{memory_mb:.1f} MB")

        # Active connections
        if "llm_active_connections" in metrics:
            connections = int(metrics["llm_active_connections"])
            table.add_row("Active Connections", str(connections))

        # Cache metrics
        if "llm_cache_hits_total" in metrics and "llm_cache_misses_total" in metrics:
            hits = metrics.get("llm_cache_hits_total", 0)
            misses = metrics.get("llm_cache_misses_total", 0)
            total_cache = hits + misses

            if total_cache > 0:
                hit_rate = (hits / total_cache) * 100
                table.add_row("Cache Hit Rate", f"{hit_rate:.1f}%")

        return table

    def create_resource_bars(self, health_data: Dict[str, Any]) -> Table:
        """Create resource usage bars."""
        table = Table(title="Resource Usage", show_header=False, box=None)
        table.add_column("Resource", style="cyan", width=15)
        table.add_column("Usage", width=40)
        table.add_column("Value", justify="right", width=15)

        resources = health_data.get("components", {}).get("system_resources", {})

        # Memory bar
        if "memory" in resources:
            mem_data = resources["memory"]["system"]
            mem_percent = mem_data.get("percent_used", 0)
            mem_bar = self._create_progress_bar(mem_percent, 100)
            table.add_row("Memory", mem_bar, f"{mem_percent:.1f}%")

        # CPU bar
        if "cpu" in resources:
            cpu_percent = resources["cpu"].get("system_percent", 0)
            cpu_bar = self._create_progress_bar(cpu_percent, 100)
            table.add_row("CPU", cpu_bar, f"{cpu_percent:.1f}%")

        # Queue bar
        queue_data = health_data.get("components", {}).get("queue", {})
        if "utilization_percent" in queue_data:
            queue_percent = queue_data["utilization_percent"]
            queue_bar = self._create_progress_bar(queue_percent, 100)
            table.add_row("Queue", queue_bar, f"{queue_percent:.1f}%")

        # Disk bar
        if "disk" in resources:
            disk_percent = resources["disk"].get("percent_used", 0)
            disk_bar = self._create_progress_bar(disk_percent, 100)
            table.add_row("Disk", disk_bar, f"{disk_percent:.1f}%")

        return table

    def _create_progress_bar(self, value: float, max_value: float, width: int = 30) -> str:
        """Create a text-based progress bar."""
        percentage = min(100, (value / max_value) * 100) if max_value > 0 else 0
        filled = int((percentage / 100) * width)

        # Determine color based on percentage
        if percentage >= 90:
            color = "red"
        elif percentage >= 70:
            color = "yellow"
        else:
            color = "green"

        bar = f"[{color}]{'█' * filled}[/{color}]{'░' * (width - filled)}"
        return bar

    async def display_live_status(self, refresh_interval: int = 5):
        """Display live updating status."""
        layout = Layout()

        with Live(layout, refresh_per_second=1, console=console):
            while True:
                try:
                    # Fetch data
                    health_data = await self.fetch_health()
                    metrics_text = await self.fetch_metrics()

                    if not health_data:
                        layout.update(
                            Panel(
                                "[red]⚠️  Cannot connect to LLM Processing Service[/red]\n\n"
                                "Make sure the service is running:\n"
                                "[cyan]python scripts/launch_llm_processing.py[/cyan]",
                                title="Service Offline",
                                border_style="red",
                            )
                        )
                    else:
                        # Parse metrics
                        metrics = self.parse_metrics(metrics_text) if metrics_text else {}

                        # Create tables
                        status_table = self.create_status_table(health_data)
                        metrics_table = self.create_metrics_table(metrics)
                        resource_bars = self.create_resource_bars(health_data)

                        # Create layout
                        layout.split_column(
                            Layout(
                                Panel(
                                    f"[bold cyan]LLM Processing Service Monitor[/bold cyan]\n"
                                    f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                    border_style="cyan",
                                ),
                                size=3,
                            ),
                            Layout(status_table),
                            Layout(metrics_table),
                            Layout(resource_bars),
                        )

                    await asyncio.sleep(refresh_interval)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    await asyncio.sleep(refresh_interval)


async def main():
    """Main function."""
    checker = StatusChecker()

    # Check if we want a one-time check or continuous monitoring
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # One-time check
        health_data = await checker.fetch_health()
        metrics_text = await checker.fetch_metrics()

        if not health_data:
            console.print("[red]⚠️  Cannot connect to LLM Processing Service[/red]")
            return 1

        # Display status
        console.print(
            Panel.fit("[bold cyan]LLM Processing Service Status[/bold cyan]", border_style="cyan")
        )

        metrics = checker.parse_metrics(metrics_text) if metrics_text else {}

        console.print(checker.create_status_table(health_data))
        console.print()
        console.print(checker.create_metrics_table(metrics))
        console.print()
        console.print(checker.create_resource_bars(health_data))

        # Return appropriate exit code
        status = health_data.get("status", "unknown")
        if status == "healthy":
            return 0
        elif status == "degraded":
            return 1
        else:
            return 2

    else:
        # Continuous monitoring
        console.print("[yellow]Starting live monitoring. Press Ctrl+C to stop.[/yellow]\n")
        await checker.display_live_status()
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
