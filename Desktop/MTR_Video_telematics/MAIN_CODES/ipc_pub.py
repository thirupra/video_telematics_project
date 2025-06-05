# ipc_publisher.py
import socket
import time
import json
import random

SERVER_ADDRESS = ("localhost", 9999)

def connect_to_subscriber():
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(SERVER_ADDRESS)
            print(" Connected to subscriber.")
            return sock
        except ConnectionRefusedError:
            print(" Waiting for subscriber...")
            time.sleep(2)

def simulate_data():
    sock = connect_to_subscriber()

    while True:
        lat = 12.97 + random.uniform(-0.01, 0.01)
        lon = 77.59 + random.uniform(-0.01, 0.01)
        speed = random.uniform(30, 80)

        if random.random() < 0.05:
            speed = random.uniform(130, 160)

        payload = {
            "latitude": lat,
            "longitude": lon,
            "speed": speed
        }

        message = json.dumps(payload) + "\n"
        try:
            sock.sendall(message.encode())
            print(" Published:", payload)
        except (BrokenPipeError, ConnectionResetError):
            print("Connection lost. Reconnecting...")
            sock.close()
            sock = connect_to_subscriber()

        time.sleep(1)

if __name__ == "__main__":
    simulate_data()

