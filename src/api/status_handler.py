import json
import os
import time
import platform
from datetime import datetime
from http.server import BaseHTTPRequestHandler

from src.database.db_manager import get_db_info
from src.config.settings import SERVER_VERSION


class StatusHandler(BaseHTTPRequestHandler):
    """Handler for status page requests."""
    
    def do_GET(self):
        """Handle GET requests for the status page."""
        if self.path == "/status" or self.path == "/status/":
            self.send_status_page()
        elif self.path == "/status/api":
            self.send_status_api()
        else:
            self.send_error(404)
    
    def send_status_page(self):
        """Send the HTML status page."""
        # Get server info
        uptime = time.time() - self.server.start_time if hasattr(self.server, "start_time") else 0
        uptime_formatted = self.format_uptime(uptime)
        
        # Get database info
        db_info = get_db_info()
        
        # Create HTML content
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>iMessage Assistant Status</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    line-height: 1.5;
                }}
                h1, h2 {{
                    color: #4A90E2;
                }}
                .status-section {{
                    margin-bottom: 30px;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    padding: 15px;
                }}
                .status-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    grid-gap: 10px;
                }}
                .status-item {{
                    margin-bottom: 10px;
                }}
                .label {{
                    font-weight: bold;
                }}
                .good {{
                    color: green;
                }}
                .warning {{
                    color: orange;
                }}
                .error {{
                    color: red;
                }}
                footer {{
                    margin-top: 30px;
                    text-align: center;
                    font-size: 0.8em;
                    color: #888;
                }}
                @media (max-width: 600px) {{
                    .status-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <h1>iMessage Assistant Status</h1>
            
            <div class="status-section">
                <h2>Server Information</h2>
                <div class="status-grid">
                    <div class="status-item">
                        <div class="label">Status:</div>
                        <div class="good">Running</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Version:</div>
                        <div>{SERVER_VERSION}</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Uptime:</div>
                        <div>{uptime_formatted}</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Server Time:</div>
                        <div>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Platform:</div>
                        <div>{platform.system()} {platform.release()}</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Python Version:</div>
                        <div>{platform.python_version()}</div>
                    </div>
                </div>
            </div>
            
            <div class="status-section">
                <h2>Database Information</h2>
                <div class="status-grid">
                    <div class="status-item">
                        <div class="label">Total Conversations:</div>
                        <div>{db_info.get('conversation_count', 'N/A')}</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Total Messages:</div>
                        <div>{db_info.get('message_count', 'N/A')}</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Total Users:</div>
                        <div>{db_info.get('user_count', 'N/A')}</div>
                    </div>
                    <div class="status-item">
                        <div class="label">Active Subscriptions:</div>
                        <div>{db_info.get('subscription_count', 'N/A')}</div>
                    </div>
                </div>
            </div>
            
            <footer>
                <p>iMessage Assistant • {datetime.now().year} • <a href="https://github.com/yourusername/imessage-assistant">GitHub</a></p>
            </footer>
        </body>
        </html>
        """
        
        # Send response
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    
    def send_status_api(self):
        """Send JSON status information."""
        # Get server info
        uptime = time.time() - self.server.start_time if hasattr(self.server, "start_time") else 0
        
        # Get database info
        db_info = get_db_info()
        
        # Create status data
        status_data = {
            "status": "running",
            "version": SERVER_VERSION,
            "uptime_seconds": int(uptime),
            "uptime_formatted": self.format_uptime(uptime),
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "platform": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version(),
            "database": db_info
        }
        
        # Send response
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(status_data).encode("utf-8"))
    
    def format_uptime(self, seconds):
        """Format uptime in seconds to a readable string."""
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0 or days > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        return ", ".join(parts) 