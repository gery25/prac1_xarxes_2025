from loguru import logger
import threading, socket, random, time
from state_machine import State_machine
from videoprocessor import VideoProcessor
from udpdatagram import UDPDatagram




class ClientHandler (threading.Thread):
    def __init__(self, client_socket, client_address):
        super().__init__() # cridar al constructor de la superclase Thread
        self.client_socket = client_socket
        self.client_address = client_address
        self.filename = None
        self.num_seq = 0
        self.client_port_udp = None
        self.socketudp = None
        self.state = State_machine()


    def run(self):
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
        lines = str(data).splitlines()

        for line in lines:
            if line.startswith("SETUP"):
                self.handle_setup(data)
                break
            elif line.startswith("PLAY"):
                self.handle_play(data)
                break
            elif line.startswith("PAUSE"):
                self.handle_pause(data)
                break
            elif line.startswith("TEARDOWN"):
                self.handle_teardown(data)
                break
            else:
                logger.debug(f'Unknown command {data}')
                break

    def handle_setup(self,data):
        logger.debug(self.state.get_state())
        if self.state.get_state() == "INIT":
            try:
                self.state.transition("SETUP")
                self.values_recived(data, "SETUP")
                setup_response = f"RTSP/1.0 200 OK\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n"
                self.client_socket.sendall(setup_response.encode())
                logger.debug(setup_response)
                self.funcion_setup()
            except Exception as e:
                logger.error(f'Error in SETUP command: {e}')
                self.client_socket.sendall(f'RTSP/1.0 500 Internal Server Error\r\n'.encode())
        else:
            logger.debug(f'The server not in state INIT')
            self.client_socket.sendall(f'RTSP/1.0 500 Internal Server Error\r\n'.encode())


    def funcion_setup(self):
        self.video = VideoProcessor(self.filename)
        self.socketudp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_udp_frame()


    def values_recived(self, data, action):
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
        prefix = "XARXES_"
        numero_aleatori = f"{random.randint(1000, 9999):04d}"
        id_session = prefix + "0000" + numero_aleatori
        return id_session

    
    def handle_play(self, data):
        if self.state.get_state() == "READY":
            try:
                self.state.transition("PLAY")
                logger.debug(f"PLAY command received")
                        
                self.values_recived(data, "PLAY")

                play_response = f"RTSP/1.0 200 OK\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n"
                self.client_socket.sendall(play_response.encode())
                logger.debug(play_response)
                        
                self.play_video_thread = threading.Thread(target=self.play_video)
                self.play_video_thread.start()
                
            except Exception as e:
                logger.debug(f"Error in PLAY command: {e}")
                self.client_socket.sendall(f"RTSP/1.0 500 Internal Server Error\r\n".encode())

    
    def play_video(self):
        """Reprodueix el vídeo enviant frames via UDP."""
        self.running = True
        while self.running:
            if not self.send_udp_frame():  # Comprova si el vídeo ha acabat
                logger.info("Vídeo finalitzat")
                self.running = False
                # Notificar al client que el vídeo ha acabat
                end_message = f"RTSP/1.0 205 END\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n"
                self.client_socket.sendall(end_message.encode())
                break

    def handle_pause(self, data):
        if self.state.get_state() == "PLAYING":
            try:
                self.state.transition("PAUSE")
                logger.debug(f"PAUSE command received")

                self.values_recived(data, "PAUSE")

                pause_response = f"RTSP/1.0 200 OK\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n"
                self.client_socket.sendall(pause_response.encode())
                logger.debug(pause_response)

                self.running = False
            except Exception as e:
                logger.debug(f"Error in PAUSE command: {e}")
                self.client_socket.sendall(f"RTSP/1.0 500 Internal Server Error\r\n")
    

    def handle_teardown(self, data):
        if self.state.get_state() in ["READY", "PLAYING"]:
            try:
                self.state.transition("TEARDOWN")
                logger.debug(f"TEARDOWN command received")

                self.values_recived(data, "TEARDOWN")

                teardown_response = f"RTSP/1.0 200 OK\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n"
                self.client_socket.sendall(teardown_response.encode())
                        
                self.break_conection()
            except Exception as e:
                logger.debug(f"Error in TEARDOWN command: {e}")
                self.client_socket.sendall(f"RTSP/1.0 500 Internal Server Error\r\n")

    def break_conection(self):
        self.running = False
        self.socketudp.close()

    def send_udp_frame(self):
        """
        Envia un frame del vídeo via UDP.
        
        Returns:
            bool: True si s'ha enviat el frame correctament, False si el vídeo ha acabat
        """
        data = self.video.next_frame()
        if data is None:  # El vídeo ha acabat
            return False
            
        if len(data) > 0:
            try:
                self.frame_number = self.video.get_frame_number()
                udp_datagram = UDPDatagram(self.frame_number, data).get_datagram()

                # Enviar el datagrama fragmentat si és necessari
                MAX_UDP_SIZE = 65507
                for i in range(0, len(udp_datagram), MAX_UDP_SIZE):
                    fragment = udp_datagram[i:i + MAX_UDP_SIZE]
                    self.socketudp.sendto(fragment, 
                                        (self.client_address[0], 
                                        int(self.client_port_udp)))
                
                time.sleep(1/25)  # Control de velocitat de reproducció
                return True
                
            except Exception as e:
                logger.error(f"Error enviant frame: {e}")
                return False
                
        return True


    def cleanup(self):
        if self.socketudp:
            self.socketudp.close()
        if self.client_socket:
            self.client_socket.close()
        logger.debug(f'Resourses cleaned up for client {self.client_address}')