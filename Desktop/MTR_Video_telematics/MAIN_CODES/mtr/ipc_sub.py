# ipc_subscriber.py
import cv2               # OpenCV for video capture and writing
import os                # For file and directory handling
import time              # For time-based operations
import json              # For decoding JSON data
import socket            # For TCP communication with publisher
import datetime          # For timestamping filenames
import threading         # For running socket listener and watchdog in parallel
from collections import deque  # For buffering pre-incident frames

# Settings
SERVER_ADDRESS = ("localhost", 9999)          # Subscriber will listen on this address and port
INCIDENT_SPEED_THRESHOLD = 120                # Speed (km/h) above which an "incident" is triggered
PRE_SECONDS = 20                              # Seconds of video to capture before the incident
POST_SECONDS = 20                             # Seconds of video to capture after the incident
FPS = 20                                      # Frames per second
RESOLUTION = (640, 480)                       # Video resolution
LOOP_DURATION_MINUTES = 20                    # Length of continuous loop recording
SILENCE_TIMEOUT = 30                          # If no data is received for this duration, treat it as post-incident

# Shared state variables
incident_triggered = False
incident_clear = False
last_data = {}                                 # Holds latest received GPS/speed data
last_message_time = time.time()                # Tracks time of last received message

# Returns formatted timestamp
def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Saves incident footage (pre + post frames)
def save_incident_clip(pre_frames, post_frames):
    os.makedirs("./incidents", exist_ok=True)
    filename = f"incident_{get_timestamp()}.mp4"
    filepath = os.path.join("./incidents", filename)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filepath, fourcc, FPS, RESOLUTION)

    for f in pre_frames + post_frames:
        out.write(f)

    out.release()
    print(f"\n Incident saved: {filepath}")

# Saves the continuous recording loop every N minutes
def save_loop_clip(writer):                                        #Saves the current continuous recording loop.
    writer.release()                                               #Finalizes the current video file.
    timestamp = get_timestamp()                                    #Gets a timestamp for naming the saved loop.
    final_path = f"./continuous/continuous_{timestamp}.mp4"              #Constructs a full path for the final loop file.
    os.makedirs("./continuous", exist_ok=True)                     #Ensures the output folder exists.
    os.rename("./Continuos_record.mp4", final_path)                     #Renames the in-progress file to a timestamped name.
    print(f" Continuous loop saved: {final_path}")

# Finds a working camera index
def find_working_camera(max_index=5):
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cap.release()
            print(f"📷 Using camera index: {i}")
            return i
        cap.release()
    return None

# Listens for data from the publisher
def socket_listener():
    global incident_triggered, incident_clear, last_data, last_message_time

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(SERVER_ADDRESS)
    server_sock.listen(1)
    print(f" Waiting for publisher on {SERVER_ADDRESS}...")

    conn, addr = server_sock.accept()
    print(f"Connected by {addr}")

    buffer = ""
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                print(" Publisher disconnected.")
                break

            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    speed = payload.get("speed", 0)
                    last_data = payload
                    last_message_time = time.time()
                    print(" Received:", payload)

                    # Detect incident
                    if speed > INCIDENT_SPEED_THRESHOLD:
                        if not incident_triggered:
                            print(f"\n High speed: {speed:.2f} km/h — incident started.")
                        incident_triggered = True
                        incident_clear = False
                    else:
                        if incident_triggered and not incident_clear:
                            print(f"\n Speed normalized ({speed:.2f} km/h) — starting post-incident buffer.")
                            incident_clear = True
                except Exception as e:
                    print("Error decoding JSON:", e)
    finally:
        conn.close()
        server_sock.close()

# Kicks in if no data received for 30 seconds during an incident
def silence_watchdog():
    global incident_triggered, incident_clear
    while True:
        time.sleep(5)
        if time.time() - last_message_time > SILENCE_TIMEOUT and incident_triggered:
            print("\n No data in 30s — treating as post-incident.")
            incident_clear = True

# Main function that handles video capture and incident recording
def monitor():
    global incident_triggered, incident_clear

    # Find available camera
    cam_index = find_working_camera()
    if cam_index is None:
        print(" No working camera found.")
        return

    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
    cap.set(cv2.CAP_PROP_FPS, FPS)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    loop_writer = cv2.VideoWriter("loop_record.mp4", fourcc, FPS, RESOLUTION)
    loop_start_time = time.time()
    max_loop_duration = LOOP_DURATION_MINUTES * 60

    pre_buffer = deque(maxlen=int(PRE_SECONDS * FPS))  # Stores pre-incident frames
    post_frames = []
    post_timer_started = False
    post_timer_start = None

    print("Recording started...")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Frame read failed.")
                break

            loop_writer.write(frame)            # Write to continuous loop video
            pre_buffer.append(frame)           # Add frame to pre-incident buffer

            # Save and start new loop file every N minutes
            if time.time() - loop_start_time >= max_loop_duration:
                save_loop_clip(loop_writer)
                loop_writer = cv2.VideoWriter("loop_record.mp4", fourcc, FPS, RESOLUTION)
                loop_start_time = time.time()
                print("Overwriting continuous loop recording...")

            # Display the live camera feed
            cv2.imshow("Live", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # Incident is active
            if incident_triggered:
                post_frames.append(frame)

                # Once vehicle slows down, start the post-incident timer
                if incident_clear:
                    if not post_timer_started:
                        post_timer_start = time.time()
                        post_timer_started = True
                    elif time.time() - post_timer_start >= POST_SECONDS:
                        print("Saving incident...")
                        save_incident_clip(list(pre_buffer), post_frames)
                        # Reset state
                        incident_triggered = False
                        incident_clear = False
                        post_timer_started = False
                        post_frames.clear()
    finally:
        cap.release()
        loop_writer.release()
        cv2.destroyAllWindows()
        print(" Camera and writer cleaned up.")

# Start the socket listener and watchdog in background threads, and run the main monitor loop
if __name__ == "__main__":
    threading.Thread(target=socket_listener, daemon=True).start()
    threading.Thread(target=silence_watchdog, daemon=True).start()
    monitor()

