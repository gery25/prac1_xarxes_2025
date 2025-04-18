from loguru import logger
from state_machine import State_machine
import socket, select, threading
import random, time
from clienthandler import ClientHandler
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
                        client_handler = ClientHandler(newsocket, addr)
                        client_handler.start()

                    
        finally:
            self.sock.close()
