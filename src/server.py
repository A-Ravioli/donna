import os
import signal
import sys
import time
from http.server import HTTPServer
from socketserver import ThreadingMixIn
import threading

from src.api.webhook_handlers import MessageWebhookHandler, StripeWebhookHandler
from src.api.status_handler import StatusHandler
from src.database.db_manager import init_db, init_users_db
from src.config.settings import SERVER_HOST, SERVER_PORT, SERVER_VERSION


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    
    def __init__(self, server_address, RequestHandlerClass, handler_map=None):
        """
        Initialize the server with a mapping of paths to handler classes.
        
        Args:
            server_address (tuple): Server address as (host, port).
            RequestHandlerClass (class): Default handler class.
            handler_map (dict, optional): Mapping of paths to handler classes.
        """
        super().__init__(server_address, RequestHandlerClass)
        self.handler_map = handler_map or {}
        self.start_time = time.time()
        

class RouterHandler:
    """Router handler that delegates to other handlers based on the path."""
    
    def __init__(self, handler_map=None):
        """
        Initialize the router handler.
        
        Args:
            handler_map (dict, optional): Mapping of paths to handler classes.
        """
        self.handler_map = handler_map or {}
        
    def __call__(self, *args, **kwargs):
        """Create a handler instance for the request."""
        handler = _RouterHandler(*args, **kwargs)
        handler.handler_map = self.handler_map
        return handler
        
        
class _RouterHandler(MessageWebhookHandler):
    """Internal handler class that routes requests to the appropriate handler."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler_map = {}
        
    def do_POST(self):
        """Route POST requests to the appropriate handler."""
        for path, handler_class in self.handler_map.items():
            if self.path.startswith(path):
                # Create and call the appropriate handler
                handler = handler_class(*self.args)
                handler.path = self.path
                handler.headers = self.headers
                handler.rfile = self.rfile
                handler.wfile = self.wfile
                handler.request = self.request
                handler.client_address = self.client_address
                handler.server = self.server
                handler.do_POST()
                return
        
        # Default to MessageWebhookHandler if no match
        super().do_POST()
        
    def do_GET(self):
        """Route GET requests to the appropriate handler."""
        if self.path.startswith("/status"):
            handler = StatusHandler(*self.args)
            handler.path = self.path
            handler.headers = self.headers
            handler.rfile = self.rfile
            handler.wfile = self.wfile
            handler.request = self.request
            handler.client_address = self.client_address
            handler.server = self.server
            handler.do_GET()
            return
            
        # If no handler matches, return 404
        self.send_error(404)


def handle_shutdown(signum, frame):
    """Handle shutdown gracefully."""
    print("Shutting down server...")
    sys.exit(0)


def main():
    """Initialize and run the server."""
    # Initialize the databases
    print("Initializing databases...")
    init_db()
    init_users_db()
    
    # Set up the handler mapping
    handler_map = {
        "/webhook/stripe": StripeWebhookHandler,
        "/webhook/message": MessageWebhookHandler,
    }
    
    # Create the router handler
    router = RouterHandler(handler_map)
    
    # Create and start the server
    host = SERVER_HOST or ""
    port = SERVER_PORT or 4321
    server = ThreadedHTTPServer((host, port), router)
    print(f"Server started on {host or '0.0.0.0'}:{port}")
    print(f"Version: {SERVER_VERSION}")
    print(f"Status page available at http://{host or '0.0.0.0'}:{port}/status")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    try:
        # Run the server
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Close the server
        server.server_close()
        print("Server stopped")


if __name__ == "__main__":
    main() 