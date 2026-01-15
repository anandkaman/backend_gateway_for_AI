"""
Interactive TUI Console
btop-like interface for monitoring and controlling the AI Gateway
"""

import asyncio
import httpx
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
import sys


class GatewayTUI:
    """Interactive terminal UI for AI Gateway management"""
    
    def __init__(self, api_url: str = "http://localhost:8080", token: str = ""):
        self.api_url = api_url
        self.token = token
        self.console = Console()
        self.running = True
        
        # Headers for API requests
        self.headers = {
            "Authorization": f"Bearer {token}",
            "X-Client-ID": "tui_console"
        }
    
    async def fetch_data(self) -> dict:
        """Fetch current status from API"""
        try:
            async with httpx.AsyncClient() as client:
                # Get model status
                models_resp = await client.get(
                    f"{self.api_url}/admin/models",
                    headers=self.headers,
                    timeout=5.0
                )
                models = models_resp.json() if models_resp.status_code == 200 else {}
                
                # Get queue metrics
                queues = {}
                for model_name in ["gemma", "deepseek"]:
                    try:
                        queue_resp = await client.get(
                            f"{self.api_url}/admin/queue/{model_name}",
                            headers=self.headers,
                            timeout=5.0
                        )
                        if queue_resp.status_code == 200:
                            queues[model_name] = queue_resp.json()
                    except:
                        pass
                
                return {
                    "models": models,
                    "queues": queues,
                    "timestamp": datetime.now()
                }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now()
            }
    
    def create_header(self) -> Panel:
        """Create header panel"""
        header_text = Text()
        header_text.append("🤖 AI Gateway Control Center", style="bold cyan")
        header_text.append(" | ", style="dim")
        header_text.append(f"API: {self.api_url}", style="dim")
        
        return Panel(header_text, style="bold blue")
    
    def create_models_panel(self, data: dict) -> Panel:
        """Create models status panel"""
        models = data.get("models", {})
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan", width=20)
        table.add_column("Status", width=12)
        table.add_column("Port", width=8)
        table.add_column("Uptime", width=15)
        table.add_column("Resolution", width=12)
        table.add_column("Health", width=10)
        
        for model_name, model_info in models.items():
            if not model_info:
                continue
            
            status = model_info.get("status", "unknown")
            status_color = {
                "running": "green",
                "stopped": "red",
                "starting": "yellow",
                "stopping": "yellow",
                "error": "red bold"
            }.get(status, "white")
            
            uptime = model_info.get("uptime_seconds", 0)
            uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m" if uptime > 0 else "-"
            
            health = "✓" if model_info.get("is_healthy") else "✗"
            health_color = "green" if model_info.get("is_healthy") else "red"
            
            resolution = model_info.get("resolution", "-")
            
            table.add_row(
                model_name,
                f"[{status_color}]{status}[/{status_color}]",
                str(model_info.get("port", "-")),
                uptime_str,
                resolution or "-",
                f"[{health_color}]{health}[/{health_color}]"
            )
        
        return Panel(table, title="📊 Models Status", border_style="blue")
    
    def create_queues_panel(self, data: dict) -> Panel:
        """Create queues status panel"""
        queues = data.get("queues", {})
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan", width=15)
        table.add_column("Processing", width=12)
        table.add_column("Waiting", width=10)
        table.add_column("Utilization", width=15)
        table.add_column("Processed", width=12)
        table.add_column("Failed", width=10)
        
        for model_name, queue_info in queues.items():
            processing = queue_info.get("processing", 0)
            waiting = queue_info.get("waiting", 0)
            max_concurrent = queue_info.get("max_concurrent", 1)
            utilization = queue_info.get("utilization", 0)
            
            # Create utilization bar
            util_bar = "█" * int(utilization * 10) + "░" * (10 - int(utilization * 10))
            util_color = "green" if utilization < 0.7 else "yellow" if utilization < 0.9 else "red"
            
            table.add_row(
                model_name,
                f"{processing}/{max_concurrent}",
                str(waiting),
                f"[{util_color}]{util_bar}[/{util_color}] {utilization*100:.0f}%",
                str(queue_info.get("total_processed", 0)),
                str(queue_info.get("total_failed", 0))
            )
        
        return Panel(table, title="📋 Queue Status", border_style="green")
    
    def create_controls_panel(self) -> Panel:
        """Create controls help panel"""
        controls = Table.grid(padding=1)
        controls.add_column(style="cyan", justify="right")
        controls.add_column(style="white")
        
        controls.add_row("q", "Quit")
        controls.add_row("r", "Refresh")
        controls.add_row("1", "Start Gemma")
        controls.add_row("2", "Start DeepSeek")
        controls.add_row("s", "Stop current model")
        controls.add_row("l/g", "Switch OCR: Large/Gundam")
        
        return Panel(controls, title="⌨️  Controls", border_style="yellow")
    
    def create_layout(self, data: dict) -> Layout:
        """Create main layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=10)
        )
        
        layout["header"].update(self.create_header())
        
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        layout["main"]["left"].split_column(
            Layout(self.create_models_panel(data)),
            Layout(self.create_queues_panel(data))
        )
        
        layout["main"]["right"].update(self.create_controls_panel())
        
        # Footer with timestamp
        timestamp = data.get("timestamp", datetime.now())
        footer_text = Text()
        footer_text.append(f"Last update: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
        
        if "error" in data:
            footer_text.append(" | ", style="dim")
            footer_text.append(f"Error: {data['error']}", style="red bold")
        
        layout["footer"].update(Panel(footer_text, style="dim"))
        
        return layout
    
    async def run(self):
        """Run the TUI"""
        self.console.clear()
        
        with Live(self.create_layout({}), refresh_per_second=1, console=self.console) as live:
            while self.running:
                # Fetch data
                data = await self.fetch_data()
                
                # Update display
                live.update(self.create_layout(data))
                
                # Wait before next update
                await asyncio.sleep(2)
    
    async def handle_input(self):
        """Handle keyboard input (simplified - would need proper async input)"""
        # This is a placeholder - proper implementation would use aioconsole or similar
        pass


async def main():
    """Main entry point"""
    import sys
    
    # Get API URL and token from args
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    token = sys.argv[2] if len(sys.argv) > 2 else ""
    
    if not token:
        print("Usage: python -m console.tui <api_url> <token>")
        print("Example: python -m console.tui http://localhost:8080 eyJ...")
        sys.exit(1)
    
    tui = GatewayTUI(api_url, token)
    
    try:
        await tui.run()
    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    asyncio.run(main())
