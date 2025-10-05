#!/usr/bin/env python3
"""
Web Shell Application - Web Interface
====================================

A Flask web application that provides a web-based terminal interface for the Docker
container shell. Users can access the container through a web browser with a
terminal-like interface powered by WebSockets for real-time communication.

Features:
- Web-based terminal interface
- Real-time bidirectional communication via WebSockets
- Terminal-like styling and behavior
- Automatic container management
- Session persistence
- Responsive design

Requirements:
- Flask for web framework
- Flask-SocketIO for WebSocket support
- Docker container management
- Real-time terminal emulation

Version: 1.0
"""

import os
import json
import threading
import time
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
import docker
import subprocess
import sys
import signal
from typing import Optional
import uuid


class DockerContainerManager:
    """
    Manages Docker container lifecycle for web interface.
    
    This class handles the creation, management, and cleanup of a Docker container
    specifically for web-based terminal access. It provides methods for container
    lifecycle management and process execution within the container.
    
    Attributes:
        client (docker.DockerClient): Docker client instance for API interactions
        container (docker.models.containers.Container): The managed container instance
        container_name (str): Fixed name for the container to ensure consistent management
        container_id (str): Unique identifier for the container
    """
    
    def __init__(self):
        """
        Initialize the DockerContainerManager.
        
        Sets up the Docker client connection and initializes container management
        attributes. The container name includes a unique identifier to prevent
        conflicts in multi-user scenarios.
        
        Raises:
            docker.errors.DockerException: If Docker daemon is not accessible
        """
        # Initialize Docker client using environment configuration
        self.client = docker.from_env()
        
        # Container instance will be set when container is created
        self.container = None
        
        # Generate unique container name to prevent conflicts
        unique_id = str(uuid.uuid4())[:8]
        self.container_name = f"web-shell-container-{unique_id}"
        self.container_id = None
        
    def create_container(self) -> bool:
        """
        Create a new Docker container with specified resource constraints.
        
        This method creates a new Docker container with the following configuration:
        - Base image: debian:12.12 (Debian Bookworm)
        - Memory limit: 256MB RAM
        - Memory swap: 256MB (prevents swap usage)
        - CPU limit: 50% of available CPU (50000/100000 quota)
        - Storage: 1GB tmpfs mounted at /tmp for temporary storage
        - Interactive mode: stdin_open and tty enabled for shell access
        
        Returns:
            bool: True if container was created successfully, False otherwise
        """
        try:
            # Clean up any existing container with the same name
            try:
                existing_container = self.client.containers.get(self.container_name)
                if existing_container.status == 'running':
                    existing_container.stop()
                existing_container.remove()
                print(f"Removed existing container: {self.container_name}")
            except docker.errors.NotFound:
                pass
            
            # Create new container with resource limits
            print(f"Creating Docker container: {self.container_name}")
            
            self.container = self.client.containers.run(
                image="debian:12.12",           # Debian Bookworm base image
                name=self.container_name,       # Unique name for this instance
                detach=True,                    # Run in background (detached mode)
                stdin_open=True,                # Keep stdin open for interactive access
                tty=True,                       # Allocate a pseudo-TTY for proper terminal
                mem_limit="256m",              # Hard limit of 256MB RAM
                memswap_limit="256m",          # Prevent swap usage beyond RAM limit
                cpu_quota=50000,               # CPU quota (50% of available CPU)
                cpu_period=100000,             # CPU period for quota calculation
                tmpfs={                        # Temporary filesystem with size limit
                    "/tmp": "size=1g"          # 1GB tmpfs mounted at /tmp
                },
                command="/bin/bash",           # Default command to run bash shell
                remove=False                   # Don't auto-remove on stop
            )
            
            self.container_id = self.container.id
            print(f"Container created successfully: {self.container_id}")
            return True
            
        except Exception as e:
            print(f"Error creating container: {e}")
            return False
    
    def start_container(self) -> bool:
        """
        Start the Docker container if it's not already running.
        
        Returns:
            bool: True if container is running (or was successfully started), False otherwise
        """
        try:
            if self.container and self.container.status != 'running':
                self.container.start()
                print("Container started successfully")
            return True
        except Exception as e:
            print(f"Error starting container: {e}")
            return False
    
    def execute_command(self, command: str) -> str:
        """
        Execute a command in the container and return the output.
        
        Args:
            command (str): The command to execute in the container
            
        Returns:
            str: The output of the command execution
        """
        try:
            if not self.container:
                return "Error: No container available"
            
            # Execute command in the container
            result = self.container.exec_run(
                command,
                stdout=True,
                stderr=True
            )
            
            # Decode the output (it comes as bytes)
            output = result.output.decode('utf-8') if isinstance(result.output, bytes) else result.output
            
            # Handle exit codes and errors
            if result.exit_code != 0:
                output = f"[Error {result.exit_code}] {output}"
            
            return output
            
        except Exception as e:
            return f"Error executing command: {e}"
    
    def get_container_info(self) -> dict:
        """
        Get comprehensive container information and statistics.
        
        Returns:
            dict: Container information including ID, name, status, and resource limits
        """
        if not self.container:
            return {"error": "No container available"}
        
        try:
            self.container.reload()
            stats = self.container.stats(stream=False)
            
            return {
                "id": self.container.id,
                "name": self.container.name,
                "status": self.container.status,
                "image": str(self.container.image),
                "memory_limit": stats['memory_stats'].get('limit', 'Unknown'),
                "created": self.container.attrs['Created']
            }
        except Exception as e:
            return {"error": f"Error getting container info: {e}"}
    
    def cleanup(self):
        """
        Clean up Docker container resources.
        
        Performs a complete cleanup of the Docker container and associated resources.
        Stops the container if it's running and removes it from the Docker daemon.
        """
        try:
            if self.container:
                if self.container.status == 'running':
                    print(f"Stopping container: {self.container_name}")
                    self.container.stop()
                
                print(f"Removing container: {self.container_name}")
                self.container.remove()
                print("Cleanup completed")
                
        except Exception as e:
            print(f"Cleanup error: {e}")


# Global container manager instance
container_manager = DockerContainerManager()

# Flask application setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'web-shell-secret-key-change-in-production')

# SocketIO setup for WebSocket communication
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


@app.route('/')
def index():
    """
    Serve the main web interface page.
    
    Returns:
        Rendered HTML template for the web terminal interface
    """
    return render_template('index.html')


@app.route('/api/container/info')
def container_info():
    """
    API endpoint to get container information.
    
    Returns:
        JSON response containing container details and statistics
    """
    info = container_manager.get_container_info()
    return jsonify(info)


@app.route('/api/container/create', methods=['POST'])
def create_container():
    """
    API endpoint to create a new container.
    
    Returns:
        JSON response indicating success or failure of container creation
    """
    try:
        success = container_manager.create_container()
        if success:
            container_manager.start_container()
            return jsonify({"success": True, "message": "Container created successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to create container"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})


@socketio.on('connect')
def handle_connect():
    """
    Handle WebSocket client connection.
    
    This function is called when a client connects to the WebSocket.
    It ensures the container is available and sends a welcome message.
    """
    print(f"Client connected: {request.sid}")
    
    # Ensure container is running
    if not container_manager.container or container_manager.container.status != 'running':
        emit('terminal_output', 'Container not running. Creating container...\r\n')
        if container_manager.create_container():
            container_manager.start_container()
            time.sleep(2)  # Wait for container to be ready
            emit('terminal_output', 'Container created and started successfully!\r\n')
        else:
            emit('terminal_output', 'Failed to create container.\r\n')
            return
    
    # Send welcome message
    emit('terminal_output', f'Welcome to Web Shell!\r\n')
    emit('terminal_output', f'Container ID: {container_manager.container_id[:12]}...\r\n')
    emit('terminal_output', f'Resources: 256MB RAM, 1GB tmpfs storage\r\n')
    emit('terminal_output', f'Type your commands below. Type "exit" to quit.\r\n\r\n')
    
    # Send shell prompt
    emit('terminal_output', '$ ')


@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle WebSocket client disconnection.
    
    This function is called when a client disconnects from the WebSocket.
    """
    print(f"Client disconnected: {request.sid}")


@socketio.on('terminal_input')
def handle_terminal_input(data):
    """
    Handle terminal input from the web client.
    
    This function processes commands sent from the web terminal interface
    and executes them in the Docker container, then sends the output back
    to the client.
    
    Args:
        data (dict): Dictionary containing the 'command' key with the user input
    """
    try:
        command = data.get('command', '').strip()
        
        if not command:
            emit('terminal_output', '$ ')
            return
        
        # Handle special commands
        if command.lower() in ['exit', 'quit']:
            emit('terminal_output', 'Exiting shell...\r\n')
            disconnect()
            return
        
        # Execute command in container
        output = container_manager.execute_command(command)
        
        # Send command output to client
        if output:
            emit('terminal_output', f'{output}\r\n')
        
        # Send shell prompt
        emit('terminal_output', '$ ')
        
    except Exception as e:
        emit('terminal_output', f'Error: {str(e)}\r\n')
        emit('terminal_output', '$ ')


def cleanup_on_exit():
    """
    Cleanup function to be called on application exit.
    
    This function ensures that the Docker container is properly cleaned up
    when the web application shuts down.
    """
    print("Cleaning up container...")
    container_manager.cleanup()


def check_docker_available():
    """
    Verify Docker daemon availability and connectivity.
    
    Returns:
        bool: True if Docker is available and accessible, False otherwise
    """
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception as e:
        print(f"Docker is not available: {e}")
        return False


def main():
    """
    Main application entry point for the web interface.
    
    This function initializes the Flask web application, checks Docker availability,
    and starts the web server with WebSocket support.
    """
    print("Web Shell Application - Web Interface")
    print("=====================================")
    
    # Check Docker availability
    if not check_docker_available():
        print("Docker is not available. Please ensure Docker is installed and running.")
        sys.exit(1)
    
    # Set up cleanup on exit
    import atexit
    atexit.register(cleanup_on_exit)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print("\nReceived interrupt signal. Cleaning up...")
        cleanup_on_exit()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting web server...")
    print("Web interface will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    # Start the Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)


if __name__ == "__main__":
    """
    Application entry point when run as a script.
    
    This ensures the main() function is only called when the script is executed
    directly, not when imported as a module.
    """
    main()
