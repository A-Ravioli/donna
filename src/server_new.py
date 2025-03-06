import os
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from dotenv import load_dotenv

from modules.database import init_db, init_users_db
from modules.http_handlers import PostHandler

# Load environment variables from .env file
load_dotenv()

# Define server port
PORT = 4321

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

def main():
    """
    Main function to start the server.
    """
    # Initialize databases
    init_db()
    init_users_db()
    
    # Create and start the server
    server = ThreadedHTTPServer(("", PORT), PostHandler)
    print(f"Threaded server started on port {PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server shutting down...")
        server.server_close()

if __name__ == "__main__":
    main() 