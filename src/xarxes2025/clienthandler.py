from loguru import logger
import threading, socket, random, time
from state_machine import State_machine
from videoprocessor import VideoProcessor
from udpdatagram import UDPDatagram




class ClientHandler (threading.Thread):
    """
    RTSP client connection handler.
    Manages video streaming for individual client connections.
    Runs in separate thread for each connected client.
    """
    def __init__(self, client_socket, client_address, options):
        """
        Initialize client handler thread.

        Args:
            client_socket: TCP socket for RTSP communication
            client_address: Client's address information
            options: Server configuration options including:
                    - max_frames: Maximum frames to stream
                    - frame_rate: Video frame rate (FPS)
        """
        super().__init__() # cridar al constructor de la superclase Thread
        self.client_socket = client_socket
        self.client_address = client_address
        self.filename = None
        self.num_seq = 0
        self.client_port_udp = None
        self.socketudp = None
        self.frame_number = 0
        self.max_frames = options.max_frames
        self.frames_rate = options.frame_rate
        self.state = State_machine()


    def run(self):
        """
        Main handler loop processing RTSP requests.
        
        Continuously receives and processes client requests.
        Handles client disconnection and cleanup.
        Catches and logs any connection errors.
        """
        try:
            while True:
                data = self.client_socket.recv(1024).decode()
                if data:
                    self.handle_request(data)
                else:
                    logger.debug(f'Connection closed by {self.client_address}')
                    break
        except Exception as e:
            logger.error(f'Error handling client {self.client_address}: {e}')
        finally:
            self.cleanup()


    def handle_request(self, data):
        """
        Process incoming RTSP request.

        Args:
            data (str): Raw RTSP request data

        Routes request to appropriate handler based on RTSP command.
        Handles unknown commands with 501 response.
        """
        
        lines = str(data).splitlines()
        handlers = {
            "SETUP": self.handle_setup,
            "PLAY": self.handle_play,
            "PAUSE": self.handle_pause,
            "TEARDOWN": self.handle_teardown
        }

        for line in lines:
            for command, handler in handlers.items():
                if line.startswith(command):
                    handler(data)
                    return
            
            logger.debug("Unknown command %s", data)
            self.send_response('501')
            break

    def handle_setup(self,data):
        """
        Process SETUP request.
        
        Verifies state is INIT.
        Initializes video streaming resources.
        Sends appropriate response code.
        """
        logger.debug(f"Current state: {self.state.get_state()}")
        if self.state.get_state() == "INIT":
            try:
                self.state.transition("SETUP")

                self.values_recived(data, "SETUP")

                self.funcion_setup()

                self.send_response('200')
            except IOError as e:
                logger.error(f'Error in SETUP command: {e}')
                self.send_response('404')
            except Exception as e:
                logger.error(f'Error in SETUP command: {e}')
                self.send_response('500')
        else:
            logger.debug(f'The server not in state INIT')
            self.send_response('500')

    def send_response(self, code):
        """
        Send RTSP response to client.

        Args:
            code (str): Response code (200, 400, 404, 500, 501)

        Formats and sends appropriate RTSP response message.
        """

        if code == '200':
            response = (f"RTSP/1.0 200 OK\r\nCSeq: {self.num_seq}\r\n"
                        f"Session: {self.session}\r\n\r\n")
        elif code == '400':
            response = f"RTSP/1.0 400 Bad Request\r\n\r\n"
        elif code == '404':
            response = f"RTSP/1.0 404 File Not Found\r\n\r\n"
        elif code == '500':
            response = f"RTSP/1.0 500 Internal Server Error\r\n\r\n"
        elif code == '501':
            response = f"RTSP/1.0 501 Not Implemented\r\n\r\n"
        
        self.client_socket.sendall(response.encode())
        logger.debug(response)


    def funcion_setup(self):
        """
        Initialize video streaming components.
        
        Creates video processor for requested file.
        Sets up UDP socket for RTP streaming.
        Sends initial video frame.
        """
        self.video = VideoProcessor(self.filename)
        self.socketudp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_udp_frame()


    def values_recived(self, data, action):
        """
        Extract values from RTSP request.

        Args:
            data (str): Raw request data
            action (str): RTSP command type

        Parses request headers for relevant information.
        Generates new session ID for SETUP requests.
        """
        lines = str(data).splitlines()
        for line in lines:
            
            if line.startswith(action):
                line = line.split(" ")
                self.filename = line[1]
                logger.debug(f"Nom del fitxer: {self.filename}")

            elif line.startswith("CSeq:"):
                self.num_seq = line.split(" ")[1]
                logger.debug(f"CSeq: {self.num_seq}")
            
            elif line.startswith("Transport:"):
                line = line.split(" ")
                self.client_port_udp = line[-1] 
                logger.debug(f"Port UDP: {self.client_port_udp}")
            
            elif line.startswith("Session:"):
                line = line.split(" ")
                self.session = line[-1] 
                logger.debug(f"Session: {self.session}")
            
        if action == "SETUP":
            self.session = self.generar_id_session()


    def generar_id_session(self):
        """
        Generate unique session identifier.
        
        Returns:
            str: Formatted session ID string
        
        Creates random session ID with prefix and padding.
        """
        prefix = "XARXES_"
        numero_aleatori = f"{random.randint(1000, 9999):04d}"
        id_session = prefix + "0000" + numero_aleatori
        return id_session

    
    def handle_play(self, data):
        """
        Process PLAY request.
    
        Args:
            data (str): Raw RTSP request data
    
        Verifies state is READY.
        Starts video streaming thread.
        Sends response to client.
        """
        if self.state.get_state() == "READY":
            try:
                self.state.transition("PLAY")
                logger.debug(f"PLAY command received")
                        
                self.values_recived(data, "PLAY")
      
                self.play_video_thread = threading.Thread(target=self.play_video)
                self.play_video_thread.start()
                
                self.send_response('200')
            except Exception as e:
                logger.debug(f"Error in PLAY command: {e}")
                self.send_response('500')
        else:
            logger.debug("Server not in READY state")
            self.send_response('500')
    
    def play_video(self):
        """
        Main video streaming loop.
    
        Continuously sends video frames via RTP.
        Controls streaming rate.
        Handles end of video condition.
        """
        self.running = True
        while self.running and (self. max_frames == None or self.frame_number < self.max_frames):
            if not self.send_udp_frame():  # Check if video is finished
                logger.info("Video streaming finished")
                self.running = False
                break

    def handle_pause(self, data):
        """
        Process PAUSE request.
    
        Args:
            data (str): Raw RTSP request data
    
        Verifies state is PLAYING.
        Stops video streaming.
        Updates client state.
        """
        if self.state.get_state() == "PLAYING":
            try:
                self.state.transition("PAUSE")
                logger.debug(f"PAUSE command received")

                self.values_recived(data, "PAUSE")

                self.running = False

                self.send_response('200')
            except Exception as e:
                logger.debug(f"Error in PAUSE command: {e}")
                self.send_response('500')
        else:
            logger.debug("Server not in PLAYING state")
            self.send_response('500')

    def handle_teardown(self, data):
        """
        Process TEARDOWN request.
    
        Args:
            data (str): Raw RTSP request data
    
        Verifies state is valid for teardown.
        Closes connection and releases resources.
        Sends final response to client.
        """
        if self.state.get_state() in ["READY", "PLAYING"]:
            try:
                self.state.transition("TEARDOWN")
                logger.debug(f"TEARDOWN command received")

                self.values_recived(data, "TEARDOWN")
                        
                self.break_conection()

                self.send_response('200')
            except Exception as e:
                logger.debug(f"Error in TEARDOWN command: {e}")
                self.send_response('500')

    def break_conection(self):
        self.running = False
        self.socketudp.close()

    def send_udp_frame(self):
        """
        Send single video frame via RTP/UDP.
    
        Returns:
            bool: True if frame sent successfully, False if video ended
    
        Fragments large frames if needed.
        Controls frame rate timing.
        """
        data = self.video.next_frame()
        if data is None:  # Video is finished
            return False
            
        if len(data) > 0:
            try:
                self.frame_number = self.video.get_frame_number()
                udp_datagram = UDPDatagram(self.frame_number, data).get_datagram()

                # Fragment if necessary
                MAX_UDP_SIZE = 65507
                for i in range(0, len(udp_datagram), MAX_UDP_SIZE):
                    fragment = udp_datagram[i:i + MAX_UDP_SIZE]
                    self.socketudp.sendto(fragment, 
                                        (self.client_address[0], 
                                        int(self.client_port_udp)))
                
                time.sleep(1/self.frames_rate)  # Control of velocity
                return True
                
            except Exception as e:
                logger.error(f"Error enviant frame: {e}")
                return False
                
        return True


    def cleanup(self):
        """
        Clean up resources on connection end.
    
        Closes:
        - UDP socket
        - TCP socket
        - Video processor
        Logs connection closure.
        """
        if self.socketudp:
            self.socketudp.close()
        if self.client_socket:
            self.client_socket.close()
        logger.debug(f'Resourses cleaned up for client {self.client_address}')