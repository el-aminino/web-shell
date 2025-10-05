#!/usr/bin/env python3
"""
Web Shell Application
====================

A Python application that creates a Docker container with limited resources and provides 
interactive shell access. The container is configured with specific resource constraints:
- 256MB RAM limit
- 1GB temporary storage via tmpfs
- CPU throttling to prevent resource abuse

The application uses the Docker Python SDK to manage container lifecycle and provides
a seamless interactive shell experience using Docker exec commands with automatic cleanup.

Features:
- Automatic container creation with resource limits
- Interactive shell access via Docker exec
- Graceful cleanup on exit or interruption
- Resource monitoring and container information display
- Signal handling for proper shutdown

Requirements:
- Python 3.7+
- Docker installed and running
- Docker daemon accessible

Version: 1.0
"""

import docker
import subprocess
import sys
import os
import signal
import time
from typing import Optional


class DockerShellManager:
    """
    Manages Docker container lifecycle and provides interactive shell access.
    
    This class handles the creation, management, and cleanup of a Docker container
    with specific resource constraints. It provides an interface for interactive
    shell access while ensuring proper resource isolation and cleanup.
    
    Attributes:
        client (docker.DockerClient): Docker client instance for API interactions
        container (docker.models.containers.Container): The managed container instance
        container_name (str): Fixed name for the container to ensure consistent management
    """
    
    def __init__(self):
        """
        Initialize the DockerShellManager.
        
        Sets up the Docker client connection and initializes container management
        attributes. The container name is fixed to ensure consistent container
        identification across application runs.
        
        Raises:
            docker.errors.DockerException: If Docker daemon is not accessible
        """
        # Initialize Docker client using environment configuration
        # This automatically detects Docker socket location and authentication
        self.client = docker.from_env()
        
        # Container instance will be set when container is created
        self.container = None
        
        # Fixed container name for consistent management
        # Allows for easy identification and cleanup of existing containers
        self.container_name = "web-shell-container"
        
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
        
        The method first removes any existing container with the same name to ensure
        a clean state. If container creation fails, the method returns False and
        logs the error.
        
        Returns:
            bool: True if container was created successfully, False otherwise
            
        Note:
            Docker doesn't provide direct storage size limits for containers.
            The 1GB limit is implemented using tmpfs mounted at /tmp, which provides
            temporary storage with the specified size constraint.
        """
        try:
            # Clean up any existing container with the same name
            # This ensures we start with a clean state and avoid naming conflicts
            try:
                existing_container = self.client.containers.get(self.container_name)
                
                # Stop the container if it's currently running
                if existing_container.status == 'running':
                    existing_container.stop()
                    print(f"Stopped existing container: {self.container_name}")
                
                # Remove the container to free up the name
                existing_container.remove()
                print(f"Removed existing container: {self.container_name}")
                
            except docker.errors.NotFound:
                # Container doesn't exist, which is fine - continue with creation
                pass
            
            # Create new container with resource limits
            print("Creating Docker container with 256MB RAM and 1GB storage...")
            
            # Container configuration with resource constraints
            # Note: Docker doesn't directly limit storage size in container creation
            # We use tmpfs for /tmp with 1GB limit as a workaround for storage limits
            self.container = self.client.containers.run(
                image="debian:12.12",           # Debian Bookworm base image
                name=self.container_name,       # Fixed name for consistent management
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
            
            print(f"Container created successfully: {self.container.id}")
            return True
            
        except Exception as e:
            print(f"Error creating container: {e}")
            return False
    
    def start_container(self) -> bool:
        """
        Start the Docker container if it's not already running.
        
        This method checks the container's current status and starts it if necessary.
        Since the container is created with detach=True, it should already be running
        after creation, but this method provides a safety check and explicit start
        capability.
        
        Returns:
            bool: True if container is running (or was successfully started), False otherwise
            
        Note:
            The container is typically already running after creation due to detach=True.
            This method serves as a verification step and handles edge cases where
            the container might not have started properly.
        """
        try:
            # Check if container exists and is not running
            if self.container and self.container.status != 'running':
                self.container.start()
                print("Container started successfully")
            else:
                # Container is already running or doesn't exist
                pass
            return True
            
        except Exception as e:
            print(f"Error starting container: {e}")
            return False
    
    def get_interactive_shell(self):
        """
        Provide interactive shell access to the Docker container.
        
        This method establishes an interactive bash shell session within the container
        using Docker's exec functionality with subprocess for better terminal compatibility.
        It provides a seamless terminal experience that behaves like a normal Linux terminal.
        
        The method displays container information and resource constraints before
        starting the interactive session. The session continues until the user types
        'exit' or 'quit', or until an error occurs.
        
        Returns:
            bool: True if shell session was established successfully, False otherwise
            
        Note:
            This implementation uses subprocess to call 'docker exec -it' directly,
            which provides better compatibility and reliability for interactive sessions
            compared to the Docker Python SDK's exec functionality.
        """
        try:
            # Validate that container exists and is available
            if not self.container:
                print("No container available")
                return False
                
            # Display session information and instructions
            print(f"\n=== Interactive Shell Access ===")
            print(f"Container ID: {self.container.id}")
            print(f"Container Name: {self.container_name}")
            print(f"Resources: 256MB RAM, 1GB tmpfs storage")
            print("Type 'exit' to quit the shell")
            print("=" * 40)
            
            # Execute interactive bash shell in the container using subprocess
            # This approach provides better terminal compatibility and behaves like a normal terminal
            docker_exec_cmd = [
                "docker", "exec",
                "-it",  # Interactive and TTY for proper terminal emulation
                self.container.id,
                "/bin/bash"
            ]
            
            # Run the interactive shell using subprocess
            # This will replace the current process with the shell session
            subprocess.run(docker_exec_cmd, check=True)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error running shell: {e}")
            return False
        except Exception as e:
            print(f"Error getting shell access: {e}")
            return False
    
    
    def cleanup(self):
        """
        Clean up Docker container resources.
        
        This method performs a complete cleanup of the Docker container and associated
        resources. It stops the container if it's currently running and then removes
        it from the Docker daemon. This ensures that no resources are left behind
        after the application exits.
        
        The cleanup process includes:
        1. Stopping the container if it's running
        2. Removing the container from Docker daemon
        3. Logging cleanup status to user
        
        This method is designed to be safe to call multiple times and handles
        various container states gracefully.
        
        Note:
            Container cleanup is essential to prevent resource leaks and ensure
            consistent behavior across application runs. The container is removed
            rather than just stopped to free up the container name for future runs.
        """
        try:
            if self.container:
                # Stop the container if it's currently running
                if self.container.status == 'running':
                    print("\nStopping container...")
                    self.container.stop()
                
                # Remove the container from Docker daemon
                print("Removing container...")
                self.container.remove()
                print("Cleanup completed")
                
        except Exception as e:
            # Log cleanup errors but don't raise them to prevent application crashes
            print(f"Cleanup error: {e}")
    
    def get_container_info(self):
        """
        Display comprehensive container information and statistics.
        
        This method retrieves and displays detailed information about the managed
        Docker container, including basic metadata and resource usage statistics.
        It refreshes the container state and retrieves current statistics from
        the Docker daemon.
        
        The displayed information includes:
        - Container ID and name
        - Current status (running, stopped, etc.)
        - Base image information
        - Memory limit configuration
        - Additional statistics from Docker stats API
        
        Note:
            This method requires the container to exist and be accessible.
            If no container is available, it displays an appropriate message
            and returns early.
        """
        if not self.container:
            print("No container available")
            return
            
        # Refresh container state to get current information
        self.container.reload()
        
        # Get current container statistics
        stats = self.container.stats(stream=False)
        
        # Display formatted container information
        print(f"\n=== Container Information ===")
        print(f"ID: {self.container.id}")
        print(f"Name: {self.container.name}")
        print(f"Status: {self.container.status}")
        print(f"Image: {self.container.image}")
        
        # Display memory limit from container statistics
        memory_limit = stats['memory_stats'].get('limit', 'Unknown')
        print(f"Memory Limit: {memory_limit} bytes")
        
        print("=" * 30)


def signal_handler(signum, frame):
    """
    Handle system interrupt signals for graceful shutdown.
    
    This function is registered as a signal handler for SIGINT (Ctrl+C) and SIGTERM
    to ensure the application shuts down gracefully when interrupted. It performs
    cleanup operations before exiting to prevent resource leaks.
    
    Args:
        signum (int): Signal number that triggered the handler
        frame: Current stack frame (unused)
        
    Note:
        The function accesses the global 'manager' variable to perform cleanup.
        If the manager doesn't exist or cleanup fails, the application still exits
        to prevent hanging in an inconsistent state.
    """
    print("\n\nReceived interrupt signal. Cleaning up...")
    
    # Perform cleanup if manager instance exists
    if 'manager' in globals():
        manager.cleanup()
    
    # Exit the application
    sys.exit(0)


def check_docker_available():
    """
    Verify Docker daemon availability and connectivity.
    
    This function checks if Docker is installed and the Docker daemon is running
    and accessible. It attempts to connect to the Docker daemon using the default
    environment configuration and performs a ping operation to verify connectivity.
    
    Returns:
        bool: True if Docker is available and accessible, False otherwise
        
    Note:
        This function should be called before attempting any Docker operations
        to provide clear error messages if Docker is not available.
    """
    try:
        # Create Docker client using environment configuration
        client = docker.from_env()
        
        # Test connectivity to Docker daemon
        client.ping()
        return True
        
    except Exception as e:
        # Docker is not available or not accessible
        print(f"Docker is not available: {e}")
        print("Please ensure Docker is installed and running")
        return False


def main():
    """
    Main application entry point and orchestration function.
    
    This function serves as the primary entry point for the Web Shell application.
    It orchestrates the entire application lifecycle from initialization to cleanup:
    
    1. Validates Docker availability
    2. Sets up signal handlers for graceful shutdown
    3. Creates and manages the Docker container
    4. Provides interactive shell access via Docker exec
    5. Performs cleanup on exit
    
    The function handles various error conditions and ensures proper resource
    cleanup regardless of how the application exits (normal exit, interrupt,
    or error).
    
    Global Variables:
        manager: DockerShellManager instance used for container management
        
    Exit Codes:
        0: Normal exit (success)
        1: Docker not available or container creation/startup failure
    """
    global manager
    
    # Display application header
    print("Web Shell Application")
    print("====================")
    
    # Validate Docker availability before proceeding
    if not check_docker_available():
        print("Cannot proceed without Docker. Exiting.")
        sys.exit(1)
    
    # Set up signal handlers for graceful shutdown
    # SIGINT: Ctrl+C interrupt signal
    # SIGTERM: Termination signal (e.g., from system shutdown)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize the Docker container manager
    manager = DockerShellManager()
    
    try:
        # Create the Docker container with resource constraints
        if not manager.create_container():
            print("Failed to create container. Exiting.")
            sys.exit(1)
        
        # Ensure container is running (should already be running after creation)
        if not manager.start_container():
            print("Failed to start container. Exiting.")
            sys.exit(1)
        
        # Allow container time to fully initialize
        # This ensures all services and processes are ready
        print("Initializing container...")
        time.sleep(2)
        
        # Display container information and resource constraints
        manager.get_container_info()
        
        # Provide interactive shell access to the user
        # This will block until the user exits the shell
        shell_success = manager.get_interactive_shell()
        
        if not shell_success:
            print("Shell session failed")
        
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully (though signal handler should catch this)
        print("\n\nApplication interrupted")
    except Exception as e:
        # Handle any unexpected errors
        print(f"Application error: {e}")
    finally:
        # Always perform cleanup, regardless of how we exit
        print("\nPerforming cleanup...")
        manager.cleanup()


if __name__ == "__main__":
    """
    Application entry point when run as a script.
    
    This ensures the main() function is only called when the script is executed
    directly, not when imported as a module. This is a Python best practice
    for creating reusable modules that can also be executed as standalone programs.
    """
    main()
