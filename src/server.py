import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from dotenv import load_dotenv

from modules.database import init_db, init_users_db
from modules.http_handlers import PostHandler, OAuthCallbackHandler
# Import the integration registry
from modules.integrations import registry

# Load environment variables from .env file
load_dotenv()

# Define server port
PORT = 4321

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    
class RequestRouter(BaseHTTPRequestHandler):
    """Route requests to the appropriate handler based on the method and path."""
    
    def do_POST(self):
        """Route POST requests."""
        # Pass the request to the PostHandler
        handler = PostHandler(self.request, self.client_address, self.server)
        handler.do_POST()
    
    def do_GET(self):
        """Route GET requests."""
        # Check if this is an OAuth callback
        if self.path.startswith("/oauth/"):
            # Pass the request to the OAuthCallbackHandler
            handler = OAuthCallbackHandler(self.request, self.client_address, self.server)
            handler.do_GET()
        else:
            # Return 404 for other GET requests
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

def main():
    """
    Main function to start the server.
    """
    # Initialize databases
    init_db()
    init_users_db()
    
    # Initialize integration registry (all integrations are automatically registered in the __init__.py)
    # The integrations are loaded and registered when the module is imported
    print(f"Loaded {len(registry.get_all_integrations())} platform integrations")
    
    # Create and start the server
    server = ThreadedHTTPServer(("", PORT), RequestRouter)
    print(f"Threaded server started on port {PORT}")
    print(f"Handling POST requests for messages and webhooks")
    print(f"Handling GET requests for OAuth callbacks")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server shutting down...")
        server.server_close()

if __name__ == "__main__":
    main() 