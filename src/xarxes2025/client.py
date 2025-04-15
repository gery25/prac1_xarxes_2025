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

class Client(object):
        

    def __init__(self, options):
        """
        Initialize a new VideoStreaming client.

        :param port: The port to connect to.
        :param filename: The filename to ask for to connect to.
        """
        self.num_seq = 0
        logger.debug(f"Client created ")
        self.options = options
        self.create_ui()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.options.destination, self.options.port))
        logger.debug(f"client params filename: {self.options.filename}, port: {self.options.port}, host: {self.options.destination}")
        print('Conected to server')

        
    def create_ui(self):
        """
        Create the user interface for the client. 

        This function creates the window for the client and its
        buttons and labels. It also sets up the window to call the
        close window function when the window is closed.

        :returns: The root of the window.
        """
        self.root = Tk()

        # Set the window title
        self.root.wm_title("RTP Client")

        # On closing window go to close window function
        self.root.protocol("WM_DELETE_WINDOW", self.ui_close_window)


		# Create Buttons
        self.setup = self._create_button("Setup", self.ui_setup_event, 0, 0)
        self.start = self._create_button("Play", self.ui_play_event, 0, 1)
        # self.pause = self._create_button("Pause", self.ui_pause_event, 0, 2)
        # self.teardown = self._create_button("Teardown", self.ui_teardown_event, 0, 3)

        # Create a label to display the movie
        self.movie = Label(self.root, height=29)
        self.movie.grid(row=1, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 

        # Create a label to display text messages
        self.text = Label(self.root, height=3)
        self.text.grid(row=2, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 

        return self.root
    
    def _create_button(self, text, command, row=0, column=0, width=20, padx=3, pady=3 ):
        """
        Create a button widget with the given text, command, and layout options.

        :param str text: The text to display on the button.
        :param callable command: The function to call when the button is clicked.
        :param int row: The row number of the button in the grid.
        :param int column: The column number of the button in the grid.
        :param int width: The width of the button.
        :param int padx: The horizontal padding of the button.
        :param int pady: The vertical padding of the button.
        :return: The button widget.
        """
        button = Button(self.root, width=width, padx=padx, pady=pady)
        button["text"] = text
        button["command"] = command
        button.grid(row=row, column=column, padx=2, pady=2)
        return button
    
    
    def ui_close_window(self):
        """
        Close the window.
        """
        self.running = False  # Aturar el thread RTP
        if hasattr(self, 'rtp_sock'):
            self.rtp_sock.close()
        self.root.destroy()
        logger.debug("Window closed")
        sys.exit(0)


    def ui_setup_event(self):
        """
        Handle the Setup button click event.
        """
        self.num_seq += 1
       
        
        try:
            local_ip, local_port = self.sock.getsockname()
            
            setup_request = f'SETUP {self.options.filename} RTSP/1.0\r\nCSeq: {self.num_seq}\r\nTransport: RTP/UDP; client_port= {local_port}\r\n'
            self.sock.sendall(setup_request.encode())
            logger.debug(setup_request)

            response = self.sock.recv(4096).decode()

            logger.debug(f"Received response from server: {response}")

            if "200 OK" in response:
                logger.info("Setup successful")

                self.rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.rtp_sock.bind((local_ip, local_port))
                logger.debug(f"RTP socket create and bound to {local_ip}:{local_port}")

                self.running = True
                self.rtp_thread = threading.Thread(target=self.receive_rtp)
                self.rtp_thread.start()
            else:
                logger.error("Setup failed")
                messagebox.showerror("Setup Error", "Setup failed. Please check the server.")
                return
        except socket.error as e:
            logger.error(f"Error connecting to server: {e}")
            messagebox.showerror("Connection Error", f"Error connecting to server: {e}")
            return
        logger.debug("Setup button clicked")
        self.text["text"] = "Setup button clicked"


    def receive_rtp(self):
        while self.running:
            try: 
                data, _ = self.rtp_sock.recv(20480)
                logger.debug(f"Received RTP packet from server")
                self.updateMovie(data)
            except socket.error as e:
                logger.error(f"Error receiving data: {e}")
                messagebox.showerror("Receive Error", f"Error receiving data: {e}")
                break

    
    def ui_play_event(self):
        """
        Handle the Play button click event.
        """
        self.num_seq += 1
        


    def updateMovie(self, data):
        """Update the video frame in the GUI from the byte buffer we received."""
        try:
            # Descodificar el payload RTP i actualitzar la pantalla
            photo = ImageTk.PhotoImage(Image.open(io.BytesIO(data)))
            self.movie.configure(image = photo, height=380)
            self.movie.photo_image = photo
        except Exception as e:
            logger.error(f"Error updating movie frame: {e}")

        

