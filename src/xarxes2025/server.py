from loguru import logger
from state_machine import State_machine
import socket, select, threading
import random, time
from udpdatagram import UDPDatagram
from videoprocessor import VideoProcessor


class Server(object):
    
    def __init__(self, port):       
        """
        Initialize a new VideoStreaming server.

        :param port: The port to listen on.
        """
        self.insocks = []
        self.outsocks = []
        self.addres = {}
        self.port = port
        self.num_seq = 0
        self.client_port_udp = None
        self.filename = None
        self.state = State_machine()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.insocks.append(self.sock)
        self.sock.bind(("", self.port))
        self.sock.listen(5)
        logger.debug(f"Server created ")
        self.main()


        
    def main(self):
        try:
            while True:
                i, o, e = select.select(self.insocks, self.outsocks, [])
                for x in i:
                    if x is self.sock:  # Una nova connexió
                        newsocket, addr = self.sock.accept()
                        logger.debug(f"New connection from {addr}")
                        self.insocks.append(newsocket)
                        self.addres[newsocket] = addr

                        # Crear un thread per gestionar aquest client
                        client_thread = threading.Thread(target=self.handle_client, args=(newsocket,))
                        client_thread.start()
                    else:
                        # Processar dades d'un client existent
                        newdata = x.recv(1024).decode()
                        if newdata:
                            self.handle_request(newdata, x)
                        else:
                            # Desconnexió del client
                            logger.debug(f"Connection closed by {self.addres[x]}")
                            del self.addres[x]
                            try:
                                self.outsocks.remove(x)
                            except ValueError:
                                pass
                            self.insocks.remove(x)
                            x.close()
        finally:
            self.sock.close()

    def handle_client(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if data:
                    self.handle_request(data, client_socket)
                else:
                    logger.debug(f"Connection closed by {self.addres[client_socket]}")
                    del self.addres[client_socket]
                    try:
                        self.outsocks.remove(client_socket)
                    except ValueError:
                        pass
                    self.insocks.remove(client_socket)
                    client_socket.close()
                    break
            except Exception as e:
                logger.error(f"Error handling client {self.addres[client_socket]}: {e}")
                break

    def handle_request(self, newdata, x):
        logger.debug(f'recive: {newdata}')
        lines = newdata.splitlines()
        # noves dades
        for line in lines:
            if line.startswith("SETUP"):
                if self.state.get_state() == "INIT":
                    try:
                        self.state.transition("SETUP")
                        logger.debug(f"SETUP command received")

                        self.funcion_setup(newdata, x)

                        setup_response = f"RTSP/1.0 200 OK\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n"
                        x.sendall(setup_response.encode())
                        logger.debug(setup_response)
                        if x not in self.outsocks:
                            self.outsocks.append(x)
                    except Exception as e:
                        logger.error(f"Error in SETUP command: {e}")
                        x.sendall(b"RTSP/1.0 500 Internal Server Error\r\n")
                else:
                    logger.error(f"Error in SETUP command: {e}")
                    x.send(f"RTSP/1.0 500 Internal Server Error\r\n".encode())      
                break
            elif line.startswith("PLAY"):
                if self.state.get_state() == "READY":
                    try:
                        self.state.transition("PLAY")
                        logger.debug(f"PLAY command received")
                        
                        self.funcion_play(newdata)

                        play_response = f"RTSP/1.0 200 OK\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n"
                        x.sendall(play_response.encode())
                        logger.debug(play_response)
                        
                        self.play_video_thread = threading.Thread(target=self.play_video, args=(x,))
                        self.play_video_thread.start()
                        logger.debug(f'send hola')
                    except Exception as e:
                        logger.debug(f"Error in PLAY command: {e}")
                        x.send(f"RTSP/1.0 500 Internal Server Error\r\n".encode())
                break
            elif line.startswith("PAUSE"):
                if self.state.get_state() == "PLAYING":
                    try:
                        self.state.transition("PAUSE")
                        logger.debug(f"PAUSE command received")

                        self.funcion_pause(newdata)

                        pause_response = f"RTSP/1.0 200 OK\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n"
                        x.sendall(pause_response.encode())
                        logger.debug(pause_response)
                        self.running = False
                    except Exception as e:
                        logger.debug(f"Error in PAUSE command: {e}")
                        x.sendall(f"RTSP/1.0 500 Internal Server Error\r\n")
                break
            elif line.startswith("TEARDOWN"):
                if self.state.get_state() in ["READY", "PLAYING"]:
                    try:
                        self.state.transition("TEARDOWN")
                        logger.debug(f"TEARDOWN command received")

                        self.funcion_teardown(newdata)

                        teardown_response = f"RTSP/1.0 200 OK\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n"
                        x.sendall(teardown_response.encode())
                        
                        self.break_conection()
                    except Exception as e:
                        logger.debug(f"Error in TEARDOWN command: {e}")
                        x.sendall(f"RTSP/1.0 500 Internal Server Error\r\n")
                break
            else:
                logger.debug(f"Unknown command {newdata}")
                break

    def funcion_setup(self, data, x):

        lines = str(data).splitlines()
        for line in lines:
            if line.startswith("SETUP"):
                line = line.split(" ")
                self.filename = line[1]
                logger.debug(f"Nom del fitxer: {self.filename}")
            elif line.startswith("CSeq:"):
                self.num_seq = line.split(" ")[-1]
                logger.debug(f"CSeq: {self.num_seq}")
            elif line.startswith("Transport:"):
                line = line.split(" ")
                self.client_port_udp = line[-1] 
                logger.debug(f"Port UDP: {self.client_port_udp}")

        logger.debug(f'num_seq: {self.num_seq} filename: {self.filename} UDPport {self.client_port_udp}')
        self.session = self.generar_id_session()
        self.video = VideoProcessor(self.filename)
        logger.debug(f'before creat upd socket')
        self.socketudp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logger.debug(f'after creat upd socket') 
        logger.debug(f'before send udp frame in setup')
        self.send_udp_frame(x)
        logger.debug(f'after send udp frame in setup')

    def generar_id_session(self):
        prefix = "XARXES_"
        numero_aleatori = f"{random.randint(1000, 9999):04d}"
        id_session = prefix + "0000" + numero_aleatori
        return id_session

        



    def funcion_play(self, data):
        """
        Function to handle the PLAY command.
        """
        # Here you would start sending the video frames over UDP
        # You will need to implement the send_udp_frame method
        
        lines = str(data).splitlines()
        for line in lines:
            if line.startswith("PLAY"):
                line = line.split(" ")
                self.filename = line[1]
                logger.debug(f"Nom del fitxer: {self.filename}")
            elif line.startswith("CSeq:"):
                self.num_seq = line.split(" ")[1]
                logger.debug(f"CSeq: {self.num_seq}")
            elif line.startswith("Session:"):
                line = line.split(" ")
                self.session = line[-1] 
                logger.debug(f"Session: {self.session}")
        

    def play_video(self, x):
        self.running = True
        while self.running:
            self.send_udp_frame(x)
            logger.debug(f'hola: {x}')

    def funcion_pause(self, data):
        """
        Function to handle the PAUSE command.
        """
        # Here you would pause the video streaming
        # You will need to implement the pause functionality
        lines = str(data).splitlines()
        for line in lines:
            if line.startswith("PAUSE"):
                line = line.split(" ")
                self.filename = line[1]
                logger.debug(f"Nom del fitxer: {self.filename}")
            elif line.startswith("CSeq:"):
                self.num_seq = line.split(" ")[1]
                logger.debug(f"CSeq: {self.num_seq}")
            elif line.startswith("Session:"):
                line = line.split(" ")
                self.session = line[-1] 
                logger.debug(f"Session: {self.session}")
        

    def funcion_teardown(self,data):
        """
        Function to handle the TEARDOWN command.
        """
        
        # Here you would stop the video streaming
        # You will need to implement the teardown functionality

        lines = str(data).splitlines()
        for line in lines:
            if line.startswith("PLAY"):
                line = line.split(" ")
                self.filename = line[1]
                logger.debug(f"Nom del fitxer: {self.filename}")
            elif line.startswith("CSeq:"):
                self.num_seq = line.split(" ")[1]
                logger.debug(f"CSeq: {self.num_seq}")
            elif line.startswith("Session:"):
                line = line.split(" ")
                self.session = line[-1] 
                logger.debug(f"Session: {self.session}")


    def break_conection(self):
        self.running = False
        self.socketudp.close()

    # # 
    # # This is not complete code, it's just an skeleton to help you get started.
    # # You will need to use these snippets to do the code.
    # # 
    # #     
    def send_udp_frame(self,x):
      
        # This snippet reads from self.video (a VideoProcessor object) and prepares 
        # the frame to be sent over UDP. 

        data = self.video.next_frame()
        if data:
            if len(data)>0:
                self.frame_number = self.video.get_frame_number()
                # create UDP Datagram

                udp_datagram = UDPDatagram(self.frame_number, data).get_datagram()

                # send UDP Datagram
                self.socketudp.sendto(udp_datagram, (self.addres[x][0], int(self.client_port_udp)))
                time.sleep(1/25)
