from loguru import logger
import socket, select
from xarxes2025.clienthandler import ClientHandler

class Server(object):
    """
    Video streaming server implementation using RTSP protocol.
    Handles multiple client connections and delegates streaming to ClientHandler threads.
    """
    
    def __init__(self, options):       
        """
        Initialize a new video streaming server.

        Args:
            options: Server configuration options including:
                    - port: TCP port to listen on
                    - host: Interface to bind to
                    - max_frames: Maximum frames to stream (None = unlimited)
                    - frame_rate: Video frame rate (FPS)
        """
        # Initialize socket lists for select()
        self.insocks = []        # Sockets to monitor for input
        self.outsocks = []       # Sockets to monitor for output
        self.addres = {}         # Address mapping for connected clients
        
        # Server configuration
        self.port = options.port
        self.options = options

        # Create and configure main server socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.insocks.append(self.sock)
        self.sock.bind(("", self.port))
        self.sock.listen(5)
        
        logger.debug(f"Server created and listening on port {self.port}")
        self.main()

    def main(self):
        """
        Main server loop handling client connections.

        Continuously:
        - Accepts new client connections
        - Creates ClientHandler threads for new clients
        - Monitors existing connections
        - Removes disconnected clients
        - Handles network errors gracefully
        """
        try:
            logger.debug("Server started and listening for connections...")
            while True:
                try:
                    # Wait for socket activity
                    readable, writable, exceptional = select.select(
                        self.insocks, self.outsocks, []
                    )

                    for sock in readable:
                        if sock is self.sock:  # New connection
                            self._handle_new_connection()
                        else:
                            self._handle_client_data(sock)

                except select.error as e:
                    logger.error(f"Select error: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    continue

        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        finally:
            self._cleanup()

    def _handle_new_connection(self):
        """
        Handle a new client connection.

        - Accepts the new connection
        - Creates a ClientHandler thread
        - Starts the handler thread
        """
        client_socket, client_address = self.sock.accept()
        logger.debug(f"New connection from {client_address}")
        
        # Create and start client handler thread
        client_handler = ClientHandler(client_socket, client_address, self.options)
        client_handler.start()

    def _handle_client_data(self, client_socket):
        """
        Handle data from an existing client.

        Args:
            client_socket: Socket of the client sending data

        - Checks for client disconnection
        - Removes disconnected clients
        - Handles connection errors
        """
        try:
            data = client_socket.recv(1024)
            if not data:  # Client disconnected
                self._remove_client(client_socket)
        except:
            logger.debug(f"Error with client {self.addres[client_socket]}"
                         f", closing connection")
            self._remove_client(client_socket)

    def _remove_client(self, client_socket):
        """
        Remove a client from the server.

        Args:
            client_socket: Socket of the client to remove

        - Removes socket from monitoring lists
        - Removes address mapping
        - Closes client socket
        """
        logger.debug(f"Client {self.addres[client_socket]} disconnected")
        self.insocks.remove(client_socket)
        del self.addres[client_socket]
        client_socket.close()

    def _cleanup(self):
        """
        Clean up server resources.

        - Closes all client sockets
        - Closes main server socket
        - Logs server shutdown
        """
        # Close all client sockets
        for sock in self.insocks:
            if sock is not self.sock:
                sock.close()
        
        # Close main server socket
        self.sock.close()
        logger.info("Server stopped correctly")
