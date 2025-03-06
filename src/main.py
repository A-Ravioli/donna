from http.server import HTTPServer
from socketserver import ThreadingMixIn
import sys
from server.handlers import PostHandler


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass


if __name__ == "__main__":
    port = 4321
    server = ThreadedHTTPServer(('', port), PostHandler)
    print(f"Threaded server started on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server")
        server.shutdown()
        sys.exit(0) 