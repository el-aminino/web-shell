# Web Shell

A Python application that creates a Docker container with limited resources and provides interactive shell access through both terminal and web interfaces.

## Features

- **Terminal Interface**: Command-line application for direct terminal access
- **Web Interface**: Browser-based terminal with real-time communication
- Creates a Docker container with 256MB RAM limit
- Provides 1GB temporary storage via tmpfs
- Interactive shell access to the container
- Automatic cleanup on exit
- Resource monitoring and container information
- Real-time WebSocket communication for web interface

## Requirements

- Python 3.7+
- Docker installed and running
- Docker daemon accessible
- Modern web browser (for web interface)

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Terminal Interface

Run the terminal application:
```bash
python app.py
```

The application will:
1. Create a new Docker container with resource limits
2. Start the container
3. Provide an interactive shell session
4. Clean up the container when you exit

### Web Interface

Run the web application:
```bash
python web_app.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

The web interface provides:
- Real-time terminal emulation
- Command history (arrow keys)
- Connection status indicator
- Container information display
- Responsive design for mobile devices

### Container Specifications

- **Memory Limit**: 256MB RAM
- **Storage**: 1GB tmpfs mounted at `/tmp`
- **CPU**: Limited to 50% of available CPU
- **Base Image**: Debian 12.12

### Exiting

**Terminal Interface:**
- Type `exit` or `quit` in the shell to end the session
- Press `Ctrl+C` to interrupt and cleanup

**Web Interface:**
- Type `exit` or `quit` in the web terminal
- Close the browser tab or stop the server with `Ctrl+C`

## Web Interface Features

- **Real-time Communication**: Uses WebSockets for instant command execution
- **Terminal-like Experience**: Full terminal emulation with proper styling
- **Command History**: Navigate through previous commands with arrow keys
- **Connection Status**: Visual indicator of connection state
- **Responsive Design**: Works on desktop and mobile devices
- **Auto-focus**: Input field automatically receives focus
- **Scroll Management**: Automatic scrolling to show latest output

## API Endpoints

The web interface provides REST API endpoints:

- `GET /api/container/info` - Get container information
- `POST /api/container/create` - Create a new container

## Notes

- The container is automatically removed when the application exits
- If a container with the same name exists, it will be removed and recreated
- The application handles Docker daemon connectivity checks
- Resource limits are enforced by Docker's cgroups
- Web interface supports multiple concurrent connections
- Each web session gets a unique container instance
