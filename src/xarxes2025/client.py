import sys, optparse, threading, time
from PIL import ImageFile
from tkinter import Tk, Label, Button, W, E, N, S
from tkinter import messagebox
import tkinter as tk

from udpdatagram import UDPDatagram
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
        """
        # Atributs de control de paquets
        self.initial_timestamp = None
        self.start_time = None
        self.last_seq_num = -1
        self.current_seq_num = 0
        self.packets_lost = 0
        self.packets_received = 0
        
        # Atributs de control RTSP
        self.num_seq = 0
        self.session = None
        self.running = False
        
        # Atributs de sockets i thread
        self.sock = None
        self.rtp_sock = None
        self.rtp_thread = None
        
        # Atributs d'UI
        self.root = None
        self.movie = None
        self.text = None
        
        # Inicialització
        self.state = State_machine()
        self.options = options
        
        logger.debug("Client creat amb estat inicial: %s", self.state.get_state())
        
        self._setup_connection()
        self.create_ui()

    def _setup_connection(self):
        """Configura la connexió inicial amb el servidor."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.options.destination, self.options.port))
            logger.debug(
                "Paràmetres del client: fitxer: %s, port: %d, host: %s",
                self.options.filename,
                self.options.port,
                self.options.destination
            )
        except socket.error as e:
            logger.error("Error connectant amb el servidor: %s", e)
            messagebox.showerror("Error de Connexió", str(e))
            raise

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
        self.pause = self._create_button("Pause", self.ui_pause_event, 0, 2)
        self.teardown = self._create_button("Teardown", self.ui_teardown_event, 0, 3)

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
        Tanca la finestra i atura el thread RTP de manera segura.
        """
        try:
            # 1. Aturar el bucle del thread
            self.running = False
            logger.debug("Aturant el thread RTP...")

            # 2. Esperar que el thread acabi (amb timeout)
            if hasattr(self, 'rtp_thread') and self.rtp_thread.is_alive():
                self.rtp_thread.join(timeout=2.0)  # Esperar màxim 2 segons
                if self.rtp_thread.is_alive():
                    logger.warning("No s'ha pogut aturar el thread RTP correctament")

            # 3. Tancar els sockets
            if hasattr(self, 'rtp_sock'):
                self.rtp_sock.close()
                logger.debug("Socket RTP tancat")
            if hasattr(self, 'sock'):
                self.sock.close()
                logger.debug("Socket RTSP tancat")

            # 4. Destruir la finestra
            self.root.destroy()
            logger.debug("Finestra tancada")

            # 5. Sortir del programa
            logger.info("Client aturat correctament")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error tancant el client: {e}")
            sys.exit(1)

    def ui_setup_event(self):
        """
        Gestiona l'esdeveniment del botó Setup.
        """
        if self.state.get_state() != "INIT":
            logger.error("El client no està en estat INIT. No es pot fer SETUP.")
            return

        self.num_seq += 1
        try:
            # Obtenir l'IP i el port locals
            local_ip, local_port = self.sock.getsockname()

            # Crear i vincular el socket RTP amb SO_REUSEADDR
            self.rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.rtp_sock.settimeout(0.5)  # Afegim un timeout de 0.5 segons
            
            # Intentar vincular el socket a diferents ports si el primer falla
            max_attempts = 10
            for port_offset in range(max_attempts):
                try:
                    bind_port = local_port + port_offset
                    self.rtp_sock.bind((local_ip, bind_port))
                    logger.debug(f"Socket RTP creat i vinculat a {local_ip}:{bind_port}")
                    local_port = bind_port  # Actualitzar el port per la petició SETUP
                    break
                except socket.error as e:
                    if port_offset == max_attempts - 1:
                        logger.error(f"No s'ha pogut crear el socket RTP després de {max_attempts} intents")
                        raise
                    continue

            # Crear i enviar la petició SETUP al servidor
            setup_request = f'SETUP {self.options.filename} RTSP/1.0\r\nCSeq: {self.num_seq}\r\nTransport: RTP/UDP; client_port= {local_port}\r\n'
            self.sock.sendall(setup_request.encode())
            logger.debug(setup_request)

            # Rebre la resposta del servidor
            response = self.sock.recv(4096).decode()
            logger.debug(f"Resposta rebuda del servidor: {response}")

            if "200 OK" in response:
                # Processar la resposta per obtenir la sessió
                lines = response.splitlines()
                for line in lines:
                    if line.startswith("Session:"):
                        self.session = line.split(":")[1].strip()
                        logger.debug(f"ID de sessió: {self.session}")
                        break

                # Canviar l'estat a READY
                if self.state.transition("SETUP"):
                    logger.debug(f"Estat canviat a: {self.state.get_state()}")
                else:
                    logger.error("Error canviant l'estat a READY.")
                logger.info("Setup correcte")
                self.text["text"] = "Setup completat"
            else:
                logger.error("Setup fallit")
                if hasattr(self, 'rtp_sock'):
                    self.rtp_sock.close()
                return

        except socket.error as e:
            logger.error("Error en el setup: %s", e)
            if hasattr(self, 'rtp_sock'):
                self.rtp_sock.close()
            return

    def receive_rtp(self):
        """
        Rep paquets RTP i processa els frames de vídeo.
        """
        frame_buffer = bytearray()  # Buffer per acumular fragments
        current_frame_num = -1

        while self.running:
            try:
                data, _ = self.rtp_sock.recvfrom(65536)
                datagram = UDPDatagram(0, b"")
                datagram.decode(data)

                # Gestió de número de seqüència
                self.current_seq_num = datagram.get_seqnum()
                
                # Si és un nou frame
                if current_frame_num != self.current_seq_num:
                    # Processar el frame anterior si existeix
                    if len(frame_buffer) > 0:
                        self.updateMovie(frame_buffer)
                    frame_buffer = bytearray()
                    current_frame_num = self.current_seq_num

                # Afegir el fragment al buffer
                frame_buffer.extend(datagram.get_payload())

                # Gestió de pèrdua de paquets
                if self.last_seq_num != -1:
                    expected_seq_num = (self.last_seq_num + 1) % 65536
                    if self.current_seq_num != expected_seq_num:
                        lost = (self.current_seq_num - expected_seq_num) % 65536
                        if lost < 100:  # Ignorem valors absurds
                            self.packets_lost += lost
                            logger.warning(f"Paquets perduts: {lost} (esperàvem {expected_seq_num}, rebut {self.current_seq_num})")

                self.last_seq_num = self.current_seq_num
                self.packets_received += 1

                # Actualitzar estadístiques
                self.text["text"] = (f'Playing: Seq Num {self.current_seq_num} | '
                                    f'Perduts: {self.packets_lost} | '
                                    f'OK: {self.packets_received}')

            except socket.timeout:
                continue
            except socket.error as e:
                logger.error("Error rebent dades: %s", e)
                break

        logger.debug("Thread RTP finalitzat")

    def ui_play_event(self):
        """
        Gestiona l'esdeveniment del botó Play.
        """
        if self.state.get_state() != "READY":
            logger.error("El client no està en estat READY. No es pot fer PLAY.")
            return

        self.num_seq += 1
        play_request = f'PLAY {self.options.filename} RTSP/1.0\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n'
        self.sock.sendall(play_request.encode())
        logger.debug(play_request)

        response = self.sock.recv(4096).decode()
        logger.debug(f"Resposta rebuda del servidor: {response}")

        if "200 OK" in response:
            self.running = True
            self.rtp_thread = threading.Thread(target=self.receive_rtp)
            self.rtp_thread.start()

            # Canviar l'estat a PLAYING
            if self.state.transition("PLAY"):
                logger.debug(f"Estat canviat a: {self.state.get_state()}")
            else:
                logger.error("Error canviant l'estat a PLAYING.")
            logger.info("Play correcte")
            self.text["text"] = "Play button clicked"
        else:
            logger.error("Play fallit")
            return
        
    
    def updateMovie(self, data):
        """
        Processa un frame complet.
        
        Args:
            frame_buffer (bytearray): Buffer amb les dades del frame
        """
        try:
            # Verificar que és un JPEG vàlid
            with io.BytesIO(data) as bio:
                img = Image.open(bio)
                img.verify()
                
            # Si la verificació és correcta, mostrar la imatge
            with io.BytesIO(data) as bio:
                img = Image.open(bio)
                photo = ImageTk.PhotoImage(img)
                self.movie.configure(image = photo, height=380)
                self.movie.photo_image = photo
                logger.debug(f"Frame mostrat correctament: {len(data)} bytes")
                
        except Exception as e:
            logger.error(f"Error processant frame: {e}")

    def ui_pause_event(self):
        """
        Gestiona l'esdeveniment del botó Pause.
        """
        if self.state.get_state() != "PLAYING":
            logger.error("El client no està en estat PLAYING. No es pot fer PAUSE.")
            return

        self.num_seq += 1
        pause_request = f'PAUSE {self.options.filename} RTSP/1.0\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n'
        self.sock.sendall(pause_request.encode())
        logger.debug(pause_request)

        response = self.sock.recv(4096).decode()
        logger.debug(f"Resposta rebuda del servidor: {response}")

        if "200 OK" in response:
            self.running = False  # Atura el thread RTP
            if self.state.transition("PAUSE"):
                logger.debug(f"Estat canviat a: {self.state.get_state()}")
            else:
                logger.error("Error canviant l'estat a READY.")
            logger.info("Pause correcte")
            self.text["text"] = "Pause button clicked"
        else:
            logger.error("Pause fallit")
            return

    def ui_teardown_event(self):
        """
        Gestiona l'esdeveniment del botó Teardown.
        """
        if self.state.get_state() not in ["READY", "PLAYING"]:
            logger.error("El client no està en un estat vàlid per fer TEARDOWN.")
            return

        self.num_seq += 1
        teardown_request = f'TEARDOWN {self.options.filename} RTSP/1.0\r\nCSeq: {self.num_seq}\r\nSession: {self.session}\r\n'
        self.sock.sendall(teardown_request.encode())
        logger.debug(teardown_request)

        response = self.sock.recv(4096).decode()
        logger.debug(f"Resposta rebuda del servidor: {response}")

        if "200 OK" in response:
            self.running = False  # Atura el thread RTP
            if hasattr(self, 'rtp_thread') and self.rtp_thread.is_alive():
                self.rtp_thread.join()  # Espera que el thread RTP acabi
            if hasattr(self, 'rtp_sock'):
                self.rtp_sock.close()  # Tanca el socket RTP
                logger.debug("Socket RTP tancat")

            # Reinicia les variables del client
            self.num_seq = 0
            self.session = None
            self.initial_timestamp = None
            self.start_time = None
            self.last_seq_num = -1  
            self.packets_lost = 0  
            self.packets_received = 0  

            # Canviar l'estat a INIT
            if self.state.transition("TEARDOWN"):
                logger.debug(f"Estat canviat a: {self.state.get_state()}")
            else:
                logger.error("Error canviant l'estat a INIT.")
            logger.info("Teardown correcte")
            self.text["text"] = "Teardown button clicked"
        else:
            logger.error("Teardown fallit")
            return