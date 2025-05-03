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

1. Install system dependencies:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv python3-dev
```

2. Install Poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Clone the repository:
```bash
git clone https://github.com/gery25/prac1_xarxes_2025.git
cd prac1_xarxes_2025
```

4. Configure Poetry to create virtual environment in project:
```bash
poetry config virtualenvs.in-project true
```

5. Install dependencies:
```bash
poetry install
```

6. Verify installation:
```bash
poetry run xarxes2025 --version
```

### Troubleshooting

If you have errors with Pillow or OpenCV:
```bash
sudo apt install libjpeg-dev zlib1g-dev libopencv-dev
poetry install
```

If you have permission issues:
```bash
# Verify video file permissions
chmod 644 *.webm
chmod 644 *.webp
```

If you need to reinstall everything:
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

2. Install dependencies:
```bash
poetry install
```

### Server Execution

```bash
# Basic execution
poetry run xarxes2025 server

# With specific port
poetry run xarxes2025 server -p 4321

# With debug mode
poetry run xarxes2025 --debug server

# With specific debug level
poetry run xarxes2025 --debug --debug-level DEBUG server
```

### Client Execution

```bash
# Basic execution
poetry run xarxes2025 client

# With specific video
poetry run xarxes2025 client rick.webm

# With specific port
poetry run xarxes2025 client -p 4321

# With all options
poetry run xarxes2025 client artificial.webm -p 4321 -h localhost -u 25000

# With debug mode
poetry run xarxes2025 --debug client rick.webm

# With detailed debug
poetry run xarxes2025 --debug --debug-level DEBUG client operating.webm
```

### Available Options

#### Global Options
- `--debug`: Enables debug mode
- `--debug-level`: Sets logging level (DEBUG, INFO, WARNING, ERROR)

#### Server Options
- `-p, --port`: RTSP port (default: 1234)
- `-h, --host`: Server IP address (default: localhost)

#### Client Options
- `-p, --port`: Server RTSP port (default: 1234)
- `-h, --host`: Server IP address (default: localhost)
- `-u, --udp-port`: Local UDP port for RTP (default: 3000)

### Available Video Files
- `rick.webm`: Main test video
- `artificial.webm`: Alternative video
- `operating.webm`: Alternative video
- `rick.webp`: Test image

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