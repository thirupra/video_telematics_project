# ipc_publisher.py
import socket       # Used for inter-process communication over TCP
import time         # Used for delays between sending messages
import json         # Used to format data as JSON strings
import random       # Used to simulate GPS and speed data

# Defining the IP address and port of the subscriber (server)
SERVER_ADDRESS = ("localhost", 9999)

def connect_to_subscriber():
    """
    Continuously attempts to connect to the subscriber (acts as a TCP client).
    Keeps trying until the subscriber becomes available.
    """
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a TCP socket
            sock.connect(SERVER_ADDRESS)                              # Attempt to connect to the subscriber
            print(" Connected to subscriber.")
            return sock                                               # Return socket if connection is successful
        except ConnectionRefusedError:
            print(" Waiting for subscriber...")                       # Subscriber not available yet
            time.sleep(2)                                             # Wait before retrying

def simulate_data():
    """
    Simulates GPS location and vehicle speed data, then sends it to the subscriber via socket.
    If the connection drops, it attempts to reconnect.
    """
    sock = connect_to_subscriber()  # Establish initial connection to subscriber

    while True:
        # Simulate GPS coordinates around a base location (Bangalore area)
        lat = 12.97 + random.uniform(-0.01, 0.01)
        lon = 77.59 + random.uniform(-0.01, 0.01)

        # Simulate normal driving speed
        speed = random.uniform(30, 80)

        # Occasionally inject a high-speed "incident" for testing
        if random.random() < 0.05:
            speed = random.uniform(130, 160)# Occasionally simulate high speed (incident)

        # Construct the message payload
        payload = {
            "latitude": lat,
            "longitude": lon,
            "speed": speed
        }

        # Convert the data to a JSON string with newline for proper message separation
        message = json.dumps(payload) + "\n"

        try:
            sock.sendall(message.encode())     # Send the message to the subscriber
            print(" Published:", payload)      # Print what was sent
        except (BrokenPipeError, ConnectionResetError):
            # Handle case when subscriber disconnects unexpectedly
            print("Connection lost. Reconnecting...")
            sock.close()
            sock = connect_to_subscriber()     # Re-establish connection

        time.sleep(1)  # Wait 1 second before sending next message

# It's the ntry point when the script is run
if __name__ == "__main__":
    simulate_data()

