import sys, threading
from tkinter import Tk, Label, Button, W, E, N, S
from tkinter import messagebox

from udpdatagram import UDPDatagram
from loguru import logger

from PIL import Image, ImageTk
import io

import socket
from state_machine import State_machine

_program__ = "client.py"
__version__ = '0.0.1'
__author__ = 'Gerard Safont <gsc23@alumnes.udl.cat>'

# Video streaming client implementation using RTP and RTSP protocols.
class Client(object):
    """
    RTP/RTSP video streaming client implementation.
    Handles video playback and communication with the streaming server.
    """

    def __init__(self, options):
        """
        Initialize a new video streaming client.

        Args:
            options: Configuration options for the client including:
                    - filename: Video file to stream
                    - host: Server hostname/IP
                    - port: Server RTSP port
                    - udp_port: Local UDP port for RTP
        """
        # Packet control attributes
        self.init_packet_control()
        
        # RTSP control attributes
        self.init_rtsp_control()
        
        # Socket and thread attributes
        self.init_socket()
        
        # UI attributes
        self.init_ui()
        
        # Initialization
        self.state = State_machine()
        self.options = options
        
        logger.debug(f"Client created with initial state: {self.state.get_state()}")
        
        self._setup_connection()
        self.create_ui()

    def init_packet_control(self):
        """
        Initialize packet control attributes for RTP statistics tracking.
        Sets up sequence numbers and packet counters.
        """
        self.initial_timestamp = None
        self.start_time = None
        self.last_seq_num = -1
        self.current_seq_num = 0
        self.packets_lost = 0
        self.packets_received = 0

    def init_rtsp_control(self):
        """
        Initialize RTSP control attributes.
        Sets up sequence number, session ID and running state.
        """
        self.num_seq = 0
        self.session = None
        self.running = False

    def init_socket(self):
        """
        Initialize socket and thread attributes.
        Sets up RTSP socket, RTP socket and RTP thread references.
        """
        self.rtsp_sock = None
        self.rtp_sock = None
        self.rtp_thread = None

    def init_ui(self): 
        """
        Inicialitza els atributs d'UI.
        """
        self.root = None
        self.movie = None
        self.text = None

    def _setup_connection(self):
        """
        Configure initial server connection.
        Creates and connects RTSP socket to specified server.
        Logs connection parameters for debugging.
        """
        try:
            self.rtsp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.rtsp_sock.connect((self.options.host, self.options.port))
            logger.debug(
                f"Client parameters: file: {self.options.filename},"
                f"port: {self.options.port}, host: {self.options.host}"
            )
        except socket.error as e:
            logger.error("Error connecting to server: %s", e)
            messagebox.showerror("Connection Error", str(e))
            raise

    def create_ui(self):
        """
        Create graphical user interface.

        Sets up main window with:
        - Title and close handler
        - Control buttons (Setup, Play, Pause, Teardown)
        - Video display label
        - Status text label
        Returns configured root window.
        """
        self.root = Tk()
        self.root.wm_title("RTP Client")  # Window title
        self.root.protocol("WM_DELETE_WINDOW", self.ui_close_window)  # Window close handler

        # Create control buttons
        self.setup = self._create_button("Setup", self.ui_setup_event, 0, 0)
        self.start = self._create_button("Play", self.ui_play_event, 0, 1)
        self.pause = self._create_button("Pause", self.ui_pause_event, 0, 2)
        self.teardown = self._create_button("Teardown", self.ui_teardown_event, 0, 3)

        # Create video display label
        self.movie = Label(self.root, height=29)
        self.movie.grid(row=1, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)

        # Create status text label
        self.text = Label(self.root, height=3)
        self.text.grid(row=2, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)

        return self.root


    def _create_button(self, text, command, row=0, column=0, width=20, padx=3, pady=3):
        """
        Create a UI button with specified parameters.

        Args:
            text (str): Button label text
            command (callable): Function to execute on click
            row (int): Grid row position
            column (int): Grid column position
            width (int): Button width
            padx (int): Horizontal padding
            pady (int): Vertical padding

        Returns:
            Button: Configured Tkinter button widget
        """
        button = Button(self.root, width=width, padx=padx, pady=pady)
        button["text"] = text
        button["command"] = command
        button.grid(row=row, column=column, padx=2, pady=2)
        return button

    def ui_close_window(self):
        """
        Close window and safely stop RTP thread.
        
        Steps:
        1. Confirm with user
        2. Stop RTP thread
        3. Close sockets
        4. Destroy window
        5. Exit application
        """
        try:
            # Ask the user if they want to close
            if messagebox.askokcancel("Quit?", 
                                "Close application?"):

                # 1. Stop the thread loop
                self.running = False
                logger.debug("RTP thread stopping...")

                # 2. Wait for the thread to end (with timeout)
                if hasattr(self, 'rtp_thread') and self.rtp_thread.is_alive():
                    self.rtp_thread.join(timeout=2.0)  # Esperar màxim 2 segons
                    if self.rtp_thread.is_alive():
                        logger.warning("Could not stop RTP thread properly")

                # 3. Close the sockets
                if hasattr(self, 'rtp_sock'):
                    self.rtp_sock.close()
                    logger.debug("RTP socket closed")
                if hasattr(self, 'rtsp_sock'):
                    self.rtsp_sock.close()
                    logger.debug("RTSP socket closed")

                # 4. Destroy the window
                self.root.destroy()
                logger.debug("Window closed")

                # 5. Get out of the program
                logger.info("Client stopped correctly")
                sys.exit(0)
        except Exception as e:
            logger.error(f"Error closing the customer: {e}")
            sys.exit(1)

    def ui_setup_event(self):
        """
        Handle Setup button event.
        
        Verifies client is in INIT state.
        Sends SETUP request and configures RTP socket.
        Updates client state on success.
        """
        if self.state.get_state() != "INIT":
            logger.error("Client not in INIT state. Cannot SETUP.")
            return

        self.num_seq += 1
        try:

            # Create and send the SETUP request to the server
            self.send_request("SETUP")

            # Receive the server response
            response = self.receive_response()

            if "200 OK" in response:

                self.create_rtp_socket()

                self.extract_session_id(response)

                # Change the state to READY
                self.change_state("SETUP")
            elif "404" in response:
                logger.error('Setup failed')
                messagebox.showerror("Error 404 File Not Found", 
                                     f"File Not Found: {self.options.filename}")
                self.ui_close_window()
            else:
                logger.error('Setup failed')
                if hasattr(self, 'rtp_sock'):
                    self.rtp_sock.close()
                return
        except socket.error as e:
            logger.error("Error during setup: %s", e)
            if hasattr(self, 'rtp_sock'):
                self.rtp_sock.close()
            return
        
    def send_request(self, command_type):
        """
        Send an RTSP request to the server.

        Args:
            command_type (str): Type of RTSP command (SETUP/PLAY/PAUSE/TEARDOWN)

        Builds and sends the appropriate RTSP request based on the command type.
        For SETUP includes transport information, for others includes session ID.
        """
        request = f"{command_type} {self.options.filename} RTSP/1.0\r\nCSeq: {self.num_seq}\r\n"

        if command_type == "SETUP":
            request += f"Transport: RTP/UDP; client_port= {self.options.udp_port}\r\n\r\n"
        else:
            request += f"Session: {self.session}\r\n\r\n"
        
        self.rtsp_sock.sendall(request.encode())
        logger.debug(request)

    def receive_response(self):
        """
        Receive and process RTSP response from server.

        Returns:
            str: Decoded response from server

        Reads response data from RTSP socket and logs it for debugging.
        """
        response = self.rtsp_sock.recv(4096).decode()
        logger.debug(f"Answer received from the server: {response}")
        return response

    def change_state(self, command_type):
        """
        Handle state transitions based on RTSP commands.

        Args:
            command_type (str): RTSP command that triggered the state change

        Updates client state machine and UI feedback.
        Logs state changes and any transition errors.
        """
        states = {"SETUP": "READY",
                 "PLAY": "PLAYING",
                 "PAUSE": "READY",
                 "TEARDOWN": "INIT"}

        if self.state.transition(command_type):
            logger.debug(f"Estat canviat a: {self.state.get_state()}")
        else:
            logger.error(f"Error changing the state to {states[command_type]}.")
            return
        logger.info(f"{command_type} successful")
        self.text["text"] = f'{command_type} completed'
        
    def create_rtp_socket(self):
        """
        Create and configure RTP socket for video streaming.

        Sets up UDP socket with:
        - SO_REUSEADDR option
        - 0.5 second timeout
        - Binds to specified host and port
        """
        # Create and link the socket RTP and SO_REUSEADDR
        self.rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.rtp_sock.settimeout(0.5)  # Add a timeout of 0.5 seconds

        # Link the socket to the specified IP and port
        self.rtp_sock.bind((self.options.host, self.options.udp_port))
        logger.debug(f"RTP socket created and bound to "
                     f"{self.options.host}:{self.options.udp_port}")
        
    def extract_session_id(self, response):
        """
        Extract session ID from RTSP response.

        Args:
            response (str): Full RTSP response from server

        Parses response headers to find and store session identifier.
        Required for subsequent RTSP requests.
        """
        # Process the answer to get the session
        lines = response.splitlines()
        for line in lines:
            if line.startswith("Session:"):
                self.session = line.split(":")[1].strip()
                logger.debug(f"Session ID: {self.session}")
                break


    def ui_play_event(self):
        """
        Handle Play button event.

        Verifies client is in READY state.
        Sends PLAY request and starts RTP reception thread.
        Updates client state on success.
        """
        if self.state.get_state() != "READY":
            logger.error("Client not in READY state. Cannot PLAY.")
            return

        self.num_seq += 1
        self.send_request("PLAY")

        response = self.receive_response()

        if "200 OK" in response:
            
            
            self.rtp_thread = threading.Thread(target=self.receive_rtp)
            self.rtp_thread.start()

            # Change the state to PLAYING
            self.change_state("PLAY")
        else:
            logger.error("Play failed")
            return

    def receive_rtp(self):
        """
        Main RTP reception loop running in separate thread.

        Continuously receives RTP packets until stopped.
        Processes video frames and updates display.
        Handles network timeouts and errors.
        """
        self._init_rtp_reception()
    
        while self.running:
            try:
                datagram = self._receive_datagram()
                if datagram:
                    self._process_datagram(datagram, self.frame_buffer, self.current_frame_num)
                    self._update_statistics()
            except socket.timeout:
                continue
            except socket.error as e:
                logger.error(f"Error receiving data: {e}")
                break

        logger.debug("Thread RTP finalitzat")

    def _init_rtp_reception(self):
        """
        Initialize RTP reception state.

        Sets up:
        - Running flag
        - Frame buffer
        - Frame numbering
        """
        self.running = True
        self.frame_buffer = bytearray()
        self.current_frame_num = -1

    def _receive_datagram(self):
        """
        Receive and decode an RTP datagram.

        Returns:
            UDPDatagram: Decoded datagram object, or None if error occurs

        - Sets large buffer size for receiving
        - Creates empty datagram
        - Decodes received data
        - Handles network and decoding errors
        """
        try:
            data, _ = self.rtp_sock.recvfrom(65536)
            datagram = UDPDatagram(0, b"")
            datagram.decode(data)
            return datagram
        except Exception as e:
            # logger.error(f"Error rebent datagrama: {e}")
            return None

    def _process_datagram(self, datagram, frame_buffer, current_frame_num):
        """
        Process a received RTP datagram.

        Args:
            datagram (UDPDatagram): Received RTP datagram
            frame_buffer (bytearray): Buffer for accumulating frame data
            current_frame_num (int): Current frame sequence number

        - Updates sequence number
        - Handles frame boundaries
        - Accumulates frame data
        - Updates packet statistics
        """
        self.current_seq_num = datagram.get_seqnum()
    
        # If is a new frame
        if current_frame_num != self.current_seq_num:
            self._handle_new_frame(frame_buffer)
            self.current_frame_num = self.current_seq_num

        # Add to the buffer
        frame_buffer.extend(datagram.get_payload())
    
        self._check_packet_loss()

        self.last_seq_num = self.current_seq_num
        self.packets_received += 1

    def _handle_new_frame(self, frame_buffer):
        """
        Process arrival of a new video frame.

        Args:
            frame_buffer (bytearray): Buffer containing previous frame data

        If buffer contains data:
        - Displays the frame
        - Clears buffer for next frame
        """
        if len(frame_buffer) > 0:
            self.updateMovie(frame_buffer)
            frame_buffer.clear()

    def _check_packet_loss(self):
        """
        Check for lost RTP packets and update statistics.

        Calculates expected sequence number.
        Detects gaps in sequence numbers.
        Updates lost packet counter.
        Logs warning messages for packet loss.
        Ignores unreasonable loss values (>100 packets).
        """
        expected_seq_num = 0
        if self.last_seq_num != -1:
            expected_seq_num = (self.last_seq_num + 1) % 65536
            if self.current_seq_num != expected_seq_num:
                lost = (self.current_seq_num - expected_seq_num) % 65536
                if lost < 100:  
                    self.packets_lost += lost
                    logger.warning(f"Lost packets: {lost} "
                                   f"(expected {expected_seq_num}, "
                                   f"received {self.current_seq_num})")


    def _update_statistics(self):
        """
        Update UI statistics display.

        Shows:
        - Current sequence number
        - Number of lost packets
        - Number of received packets
        Updates text label with formatted statistics string.
        """
        self.text["text"] = (f'Playing: Seq Num {self.current_seq_num} | '
                             f'Lost: {self.packets_lost} | '
                             f'OK: {self.packets_received}')

    
    def updateMovie(self, data):
        """
        Process and display a video frame.

        Args:
            data (bytearray): JPEG encoded frame data

        - Creates BytesIO object from frame data
        - Opens and verifies JPEG image
        - Converts to Tkinter PhotoImage
        - Updates UI label with new frame
        - Handles image processing errors
        """
        try:
            with io.BytesIO(data) as bio:
                # Open and verify image
                img = Image.open(bio)
                img.load()  # Verify and load image at once
            
                # Convert to Tkinter format
                photo = ImageTk.PhotoImage(img)
                self.movie.configure(image=photo, height=380)
                self.movie.photo_image = photo
            
                # logger.debug(f"Frame mostrat correctament: {len(data)} bytes")    
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
        
    def ui_pause_event(self):
        """
        Handle Pause button event.

        Verifies client is in PLAYING state.
        Sends PAUSE request to stop video streaming.
        Stops RTP reception thread on success.
        Updates client state to READY.
        """
        if self.state.get_state() != "PLAYING":
            logger.error("Client not in PLAYING state. Cannot PAUSE.")
            return

        self.num_seq += 1

        self.send_request("PAUSE")

        response = self.receive_response()

        if "200 OK" in response:
            self.running = False  # Stop RTP thread
            
            self.change_state("PAUSE")
        else:
            logger.error("Pause failed")
            return

    def ui_teardown_event(self):
        """
        Handle Teardown button event.

        Verifies client is in valid state (READY or PLAYING).
        Sends TEARDOWN request to end streaming session.
        Cleans up resources:
        - Stops RTP thread
        - Closes RTP socket
        - Resets client state to INIT
        - Reinitializes control variables
        """
        if self.state.get_state() not in ["READY", "PLAYING"]:
            logger.error("Client not in valid state for TEARDOWN.")
            return

        self.num_seq += 1

        self.send_request("TEARDOWN")

        response = self.receive_response()

        if "200 OK" in response:
            self.running = False  # Stop RTP thread
            if hasattr(self, 'rtp_thread') and self.rtp_thread.is_alive():
                self.rtp_thread.join(timeout=2.0)

            if hasattr(self, 'rtp_sock'):
                self.rtp_sock.close()  # Tanca el socket RTP
                logger.debug("RTP socket closed")

            # Reset client variables
            self. init_packet_control()
            self.init_rtsp_control()

            # Change state to INIT
            self.change_state("TEARDOWN")
        else:
            logger.error("Teardown failed")
            return