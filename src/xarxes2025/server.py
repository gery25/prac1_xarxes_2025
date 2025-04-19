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
        """
        Bucle principal del servidor que gestiona les connexions dels clients.
        """
        try:
            logger.debug("Servidor iniciat i escoltant connexions...")
            while True:
                try:
                    i, o, e = select.select(self.insocks, self.outsocks, [])
                    for x in i:
                        if x is self.sock:  # Nova connexió
                            newsocket, addr = self.sock.accept()
                            logger.debug(f"Nova connexió des de {addr}")

                            # Crear un thread per gestionar aquest client
                            client_handler = ClientHandler(newsocket, addr)
                            client_handler.start()
                        else:
                            # Si un client es desconnecta, eliminem el seu socket
                            try:
                                data = x.recv(1024)
                                if not data:
                                    logger.debug(f"Client {self.addres[x]} desconnectat")
                                    self.insocks.remove(x)
                                    del self.addres[x]
                                    x.close()
                            except:
                                logger.debug(f"Error amb el client {self.addres[x]}, tancant connexió")
                                self.insocks.remove(x)
                                del self.addres[x]
                                x.close()

                except select.error as e:
                    logger.error(f"Error en select: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error inesperat: {e}")
                    continue

        except KeyboardInterrupt:
            logger.info("Servidor aturat per l'usuari")
        finally:
            # Tancar tots els sockets clients
            for sock in self.insocks:
                if sock is not self.sock:
                    sock.close()
            # Tancar el socket principal
            self.sock.close()
            logger.info("Servidor aturat correctament")
