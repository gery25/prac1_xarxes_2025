import sys, optparse, threading

from tkinter import Tk, Label, Button, W, E, N, S
from tkinter import messagebox
import tkinter as tk


from loguru import logger

from PIL import Image, ImageTk
import io

import socket
from state_machine import State_machine

_program__ = "client.py"
__version__ = '0.0.1'
__author__ = 'Gerard Safont <gsc23@alumnes.udl.cat>'

# Aquesta classe representa un client de streaming de vídeo que utilitza RTP i RTSP.
class Client(object):
    def __init__(self, options):
        """
        Inicialitza un nou client de streaming de vídeo.

        :param options: Opcions de configuració com el port, el fitxer i la destinació.
        """
        self.num_seq = 0  # Número de seqüència RTSP.
        logger.debug(f"Client creat")
        self.options = options
        self.create_ui()  # Crear la interfície gràfica d'usuari.
        try:
            # Crear un socket TCP per connectar-se al servidor.
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.options.destination, self.options.port))
            logger.debug(f"Paràmetres del client: fitxer: {self.options.filename}, port: {self.options.port}, host: {self.options.destination}")
        except socket.error as e:
            # Gestionar errors de connexió.
            logger.error(f"Error connectant amb el servidor: {e}")
            messagebox.showerror("Error de Connexió", f"Error connectant amb el servidor: {e}")
            return
        print('Connectat al servidor')

    def create_ui(self):
        """
        Crea la interfície gràfica d'usuari per al client.

        Aquesta funció configura la finestra, els botons i les etiquetes.
        """
        self.root = Tk()
        self.root.wm_title("RTP Client")  # Títol de la finestra.
        self.root.protocol("WM_DELETE_WINDOW", self.ui_close_window)  # Acció en tancar la finestra.

        # Crear botons per a les accions Setup i Play.
        self.setup = self._create_button("Setup", self.ui_setup_event, 0, 0)
        self.start = self._create_button("Play", self.ui_play_event, 0, 1)

        # Crear una etiqueta per mostrar el vídeo.
        self.movie = Label(self.root, height=29)
        self.movie.grid(row=1, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)

        # Crear una etiqueta per mostrar missatges de text.
        self.text = Label(self.root, height=3)
        self.text.grid(row=2, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)

        return self.root

    def _create_button(self, text, command, row=0, column=0, width=20, padx=3, pady=3):
        """
        Crea un botó amb el text, la funció associada i les opcions de disseny especificades.

        :param str text: Text del botó.
        :param callable command: Funció a executar en fer clic.
        :return: El widget del botó.
        """
        button = Button(self.root, width=width, padx=padx, pady=pady)
        button["text"] = text
        button["command"] = command
        button.grid(row=row, column=column, padx=2, pady=2)
        return button

    def ui_close_window(self):
        """
        Tanca la finestra i atura el thread RTP.
        """
        self.running = False  # Aturar el thread RTP.
        if hasattr(self, 'rtp_sock'):
            self.rtp_sock.close()  # Tancar el socket RTP.
        self.root.destroy()  # Tancar la finestra.
        logger.debug("Finestra tancada")
        sys.exit(0)

    def ui_setup_event(self):
        """
        Gestiona l'esdeveniment del botó Setup.
        """
        self.num_seq += 1  # Incrementar el número de seqüència RTSP.
        try:
            # Obtenir l'IP i el port locals.
            local_ip, local_port = self.sock.getsockname()

            # Crear i enviar la petició SETUP al servidor.
            setup_request = f'SETUP {self.options.filename} RTSP/1.0\r\nCSeq: {self.num_seq}\r\nTransport: RTP/UDP; client_port= {local_port}\r\n'
            self.sock.sendall(setup_request.encode())
            logger.debug(setup_request)

            # Rebre la resposta del servidor.
            response = self.sock.recv(4096).decode()
            logger.debug(f"Resposta rebuda del servidor: {response}")

            # Processar la resposta per obtenir la sessió.
            lines = response.splitlines()
            for lin in lines:
                if lin.startswith("Session:"):
                    self.session = lin.split(":")[1].strip()
                    logger.debug(f"ID de sessió: {self.session}")
                    break

            if "200 OK" in response:
                # Configuració exitosa.
                logger.info("Setup correcte")
                try:
                    # Crear i vincular el socket RTP.
                    self.rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.rtp_sock.bind((local_ip, local_port))
                    logger.debug(f"Socket RTP creat i vinculat a {local_ip}:{local_port}")
                except socket.error as e:
                    logger.error(f"Error creant el socket RTP: {e}")
                    messagebox.showerror("Error de Socket", f"Error creant el socket RTP: {e}")
                    return
                self.running = True
                # Iniciar un thread per rebre paquets RTP.
                self.rtp_thread = threading.Thread(target=self.receive_rtp)
                self.rtp_thread.start()
            else:
                # Error en la configuració.
                logger.error("Setup fallit")
                messagebox.showerror("Error de Setup", "Setup fallit. Comprova el servidor.")
                return
        except socket.error as e:
            # Error de connexió amb el servidor.
            logger.error(f"Error connectant amb el servidor: {e}")
            messagebox.showerror("Error de Connexió", f"Error connectant amb el servidor: {e}")
            return
        logger.debug("Botó Setup clicat")
        self.text["text"] = "Botó Setup clicat"

    def receive_rtp(self):
        """
        Rep paquets RTP i processa els frames de vídeo.
        """
        buffer = bytearray()  # Buffer per emmagatzemar dades rebudes.
        while self.running:
            try:
                # Rebre dades del socket RTP.
                data, _ = self.rtp_sock.recvfrom(20480)
                if data:
                    logger.debug(f'Dades: {data}')
                    logger.debug(f"Paquet RTP rebut de mida {len(data)} bytes")
                    buffer.extend(data)

                    # Extreure un frame del buffer.
                    frame = self.extract_frame(buffer)
                    if frame:
                        logger.debug(f"Frame extret de mida {len(frame)} bytes")
                        self.updateMovie(frame)  # Actualitzar el vídeo a la GUI.
                else:
                    logger.warning("No s'han rebut dades del socket RTP")
            except socket.error as e:
                # Error en rebre dades.
                logger.error(f"Error rebent dades: {e}")
                messagebox.showerror("Error de Recepció", f"Error rebent dades: {e}")
                break

    def ui_play_event(self):
        """
        Handle the Play button click event.
        """
        self.num_seq += 1
        play_request = f'PLAY {self.options.filename} RTSP/1.0\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n'
        self.sock.sendall(play_request.encode())
        logger.debug(play_request)

        response = self.sock.recv(4096).decode()
        logger.debug(f"Received response from server: {response}")

        if "200 OK" in response:
            

            self.running = True
            self.rtp_thread = threading.Thread(target=self.receive_rtp)
            self.rtp_thread.start()

            logger.info("Play successful")
            self.text["text"] = "Play button clicked"

        else:
            logger.error("Play failed")
            messagebox.showerror("Play Error", "Play failed. Please check the server.")
            return
        

    def extract_frame(self, buffer):
        try:
            if len(buffer) < 12:
               return None
            # Extract the RTP header
            frame_size = int.from_bytes(buffer[:4], byteorder='big')
            if len(buffer) < frame_size + 12:
                return None
            frame = buffer[4:frame_size + 4]
            del buffer[:frame_size + 12]
            return frame
        except Exception as e:
            logger.error(f"Error extracting frame: {e}")
            return None


    def updateMovie(self, data):
        """Update the video frame in the GUI from the byte buffer we received."""
        try:
            logger.debug(f"Updating movie frame")
            # Descodificar el payload RTP i actualitzar la pantalla
            photo = ImageTk.PhotoImage(Image.open(io.BytesIO(data)))
            logger.debug(f"Image size: {photo.width()} x {photo.height()}")
            self.movie.configure(image = photo, height=380)
            self.movie.photo_image = photo
            self.text["text"] = f'Playing: Seq Num {self.num_seq} lost: {0} OK: {1}'
        except Exception as e:
            logger.error(f"Error updating movie frame: {e}")



