from http.server import HTTPServer
from socketserver import ThreadingMixIn
from donna.server.handlers import PostHandler
from donna.database.models import init_db, init_users_db

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """
    Handle requests in a separate thread.
    """
    pass


def start_server(port=4321):
    """
    Start the server on the specified port.

    Args:
        port (int): The port to listen on
    """
    # Initialize the databases
    init_db()
    init_users_db()
    
    # Create and start the server
    server = ThreadedHTTPServer(("", port), PostHandler)
    print(f"Threaded server started on port {port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped by user")
    finally:
        server.server_close()
        print("Server stopped") 