# Xarxes2025 Video Streaming

A video streaming application using RTSP/RTP protocols implemented in Python.

## Description

This project implements a client-server video streaming solution using:
- RTSP (Real Time Streaming Protocol) for session control
- RTP (Real-time Transport Protocol) for video data transmission
- UDP for video frame delivery

## Requirements

- Python >= 3.8.1
- Poetry for dependency management
- OpenCV for video processing
- Pillow for image handling
- Click for CLI interface
- Loguru for logging

## Installation

1. Instal·la les dependències del sistema:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv python3-dev
```

2. Instal·la Poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Clona el repositori:
```bash
git clone https://github.com/gery25/prac1_xarxes_2025.git
cd prac1_xarxes_2025
```

4. Configura Poetry per crear l'entorn virtual al projecte:
```bash
poetry config virtualenvs.in-project true
```

5. Instal·la les dependències:
```bash
poetry install
```

6. Verifica la instal·lació:
```bash
poetry run xarxes2025 --version
```

### Resolució de problemes

Si tens errors amb Pillow o OpenCV:
```bash
sudo apt install libjpeg-dev zlib1g-dev libopencv-dev
poetry install
```

Si tens problemes amb els permisos:
```bash
# Verifica els permisos dels fitxers de vídeo
chmod 644 *.webm
chmod 644 *.webp
```

Si necessites reinstal·lar tot:
```bash
rm -rf .venv/
rm -f poetry.lock
poetry lock
poetry install
```

## Usage

1. Start the server:
```bash
# Basic usage
poetry run xarxes2025 server

# With options
poetry run xarxes2025 server --port 4321 --host localhost --max-frames 100 --frame-rate 25
```

2. Start the client:
```bash
# Basic usage
poetry run xarxes2025 client

# With specific video file
poetry run xarxes2025 client rick.webm

# With all options
poetry run xarxes2025 client video.webm -p 4321 -h localhost -u 25000
```

### Debug Options

Both server and client support debug options:
```bash
# Enable debug logging
poetry run xarxes2025 --debug client

# Set debug level
poetry run xarxes2025 --debug --debug-level DEBUG client

# Log to file
poetry run xarxes2025 --debug --debug-file --debug-filename debug.log client
```

## Project Structure

```
xarxes2025/
├── __init__.py          # Package initialization and version
├── __main__.py         # Entry point for CLI
├── cli.py              # Command line interface implementation
├── client.py           # RTSP client implementation
├── clienthandler.py    # Server's client handler
├── server.py           # RTSP server implementation
├── state_machine.py    # RTSP state machine
├── udpdatagram.py      # RTP packet handling
├── videoprocessor.py   # Video frame processing
├── artificial.webm     # Sample video file
├── operating.webm      # Sample video file
├── rick.webm          # Sample video file
└── rick.webp          # Sample image file
```

## Features

- RTSP session management (SETUP, PLAY, PAUSE, TEARDOWN)
- RTP video streaming over UDP
- Real-time video display
- Packet loss detection
- Frame rate control
- Debug logging
- Multiple client support
- GUI client interface

## Development

1. Activate virtual environment:
```bash
poetry shell
```

2. Instal·lar dependències:
```bash
poetry install
```

### Execució del servidor

```bash
# Execució bàsica
poetry run xarxes2025 server

# Amb port específic
poetry run xarxes2025 server -p 4321

# Amb mode debug
poetry run xarxes2025 --debug server

# Amb nivell de debug específic
poetry run xarxes2025 --debug --debug-level DEBUG server
```

### Execució del client

```bash
# Execució bàsica
poetry run xarxes2025 client

# Amb vídeo específic
poetry run xarxes2025 client rick.webm

# Amb port específic
poetry run xarxes2025 client -p 4321

# Amb totes les opcions
poetry run xarxes2025 client artificial.webm -p 4321 -h localhost -u 25000

# Amb mode debug
poetry run xarxes2025 --debug client rick.webm

# Amb debug detallat
poetry run xarxes2025 --debug --debug-level DEBUG client operating.webm
```

### Opcions disponibles

#### Opcions globals
- `--debug`: Activa el mode debug
- `--debug-level`: Estableix el nivell de logging (DEBUG, INFO, WARNING, ERROR)

#### Opcions del servidor
- `-p, --port`: Port RTSP (per defecte: 1234)
- `-h, --host`: Adreça IP del servidor (per defecte: localhost)

#### Opcions del client
- `-p, --port`: Port RTSP del servidor (per defecte: 1234)
- `-h, --host`: Adreça IP del servidor (per defecte: localhost)
- `-u, --udp-port`: Port UDP local per RTP (per defecte: 3000)

### Fitxers de vídeo disponibles
- `rick.webm`: Vídeo principal de prova
- `artificial.webm`: Vídeo alternatiu
- `operating.webm`: Vídeo alternatiu
- `rick.webp`: Imatge de prova

## Configuration

Server options:
- `--port`: RTSP port (default: 4321)
- `--host`: Server IP address (default: localhost)
- `--max-frames`: Maximum frames to stream (default: None)
- `--frame-rate`: Frames per second (default: 25)

Client options:
- `--port`: Server RTSP port (default: 4321)
- `--host`: Server IP address (default: localhost)
- `--udp-port`: Local UDP port for RTP (default: 25000)

## Authors

Gerard Safont <gsc23@alumnes.udl.cat> or <gerymaps200515@gmail.com>

## Acknowledgments

This project is based on the skeleton code from [xarxes2025](https://github.com/carlesm/xarxes2025.git) by Carles Mateu. The original codebase was used as a starting point and has been modified and enhanced to meet the requirements of this project.