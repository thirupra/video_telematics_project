import cv2
import os
import time
import json
import paho.mqtt.client as mqtt
from collections import deque
import datetime
import threading

# === CONFIG ===
BROKER = "localhost"
TOPIC = "vehicle/data"
INCIDENT_SPEED_THRESHOLD = 120  # km/h
PRE_SECONDS = 20
POST_SECONDS = 20
FPS = 20.0
RESOLUTION = (640, 480)
SILENCE_TIMEOUT = 30  # seconds without MQTT message
LOOP_DURATION_MINUTES = 60  # continuous recording duration before overwrite

# === HELPER ===
def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def save_incident_clip(pre_frames, post_frames, resolution, fps):
    save_dir = "./incidents"
    os.makedirs(save_dir, exist_ok=True)
    filename = f"incident_{get_timestamp()}.mp4"
    filepath = os.path.join(save_dir, filename)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filepath, fourcc, fps, resolution)

    for frame in pre_frames:
        out.write(frame)
    for frame in post_frames:
        out.write(frame)

    out.release()
    print(f"\n🚨 Incident saved: {filepath}\n")

def save_loop_clip(writer):
    writer.release()
    timestamp = get_timestamp()
    final_path = f"./continuous/loop_{timestamp}.mp4"
    os.makedirs("./continuous", exist_ok=True)
    os.rename("./loop_record.mp4", final_path)
    print(f"💾 Continuous loop saved: {final_path}")

def find_working_camera(max_index=5):
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cap.release()
            print(f"✅ Using camera index: {i}")
            return i
        cap.release()
    print("❌ No working camera found.")
    return None

# === GLOBALS ===
incident_triggered = False
incident_clear = False
last_data = {}
last_message_time = time.time()

# === MQTT CALLBACK ===
def on_message(client, userdata, msg):
    global incident_triggered, incident_clear, last_data, last_message_time
    last_message_time = time.time()
    try:
        if not msg.payload:
            return
        payload = json.loads(msg.payload.decode())
        speed = payload.get("speed", 0)
        last_data = payload

        if speed > INCIDENT_SPEED_THRESHOLD:
            if not incident_triggered:
                print(f"\n🚧 High speed detected ({speed:.2f} km/h) — incident started...")
            incident_triggered = True
            incident_clear = False
        else:
            if incident_triggered and not incident_clear:
                print(f"\n✅ Speed normalized ({speed:.2f} km/h) — starting post-incident buffer...")
                incident_clear = True
    except json.JSONDecodeError:
        print("⚠️ Invalid JSON payload")
    except Exception as e:
        print("❌ MQTT error:", e)

# === MQTT SETUP ===
def start_mqtt():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(BROKER, 1883, 60)
    client.subscribe(TOPIC)
    client.loop_start()

# === SILENCE WATCHDOG ===
def silence_watchdog():
    global incident_triggered, incident_clear, post_timer_started, post_timer_start
    while True:
        time.sleep(5)
        if time.time() - last_message_time > SILENCE_TIMEOUT:
            if incident_triggered:
                print("\n⚠️ No MQTT messages for 30s — treating as post-incident.")
                incident_clear = True

# === MAIN CAMERA LOOP ===
def monitor():
    global incident_triggered, incident_clear
    CAMERA_INDEX = find_working_camera()
    if CAMERA_INDEX is None:
        return

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
    cap.set(cv2.CAP_PROP_FPS, FPS)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    loop_path = "./loop_record.mp4"
    os.makedirs("./continuous", exist_ok=True)
    loop_writer = cv2.VideoWriter(loop_path, fourcc, FPS, RESOLUTION)
    loop_start_time = time.time()
    max_loop_duration = LOOP_DURATION_MINUTES * 60

    pre_buffer = deque(maxlen=int(PRE_SECONDS * FPS))
    post_frames = []
    post_timer_started = False
    post_timer_start = None

    print("🎥 Camera recording started with incident monitoring via MQTT...")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Frame read failed.")
                break

            loop_writer.write(frame)
            pre_buffer.append(frame)

            if time.time() - loop_start_time >= max_loop_duration:
                save_loop_clip(loop_writer)
                loop_writer = cv2.VideoWriter(loop_path, fourcc, FPS, RESOLUTION)
                loop_start_time = time.time()
                print("🔁 Overwriting continuous loop recording...")

            cv2.imshow("Live Recording", frame)
            if cv2.waitKey(1) & 0xFF == ord('s'):
                break

            if incident_triggered:
                post_frames.append(frame)

                if incident_clear:
                    if not post_timer_started:
                        post_timer_start = time.time()
                        post_timer_started = True

                    elif time.time() - post_timer_start >= POST_SECONDS:
                        print("💾 Saving incident clip...")
                        save_incident_clip(list(pre_buffer), post_frames, RESOLUTION, FPS)
                        incident_triggered = False
                        incident_clear = False
                        post_timer_started = False
                        post_frames.clear()

    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")

    finally:
        cap.release()
        save_loop_clip(loop_writer)
        cv2.destroyAllWindows()
        print("✅ Cleaned up camera and writer.")

if __name__ == "__main__":
    start_mqtt()
    threading.Thread(target=silence_watchdog, daemon=True).start()
    monitor()

