import cv2
import os
import time
import json
import threading
import datetime
import paho.mqtt.client as mqtt
from collections import deque

# === Configuration ===
MQTT_BROKER = "localhost"
MQTT_TOPIC = "vehicle/data"

SPEED_LIMIT = 120  # km/h threshold for incident detection
PRE_EVENT_DURATION = 20  # seconds to buffer before incident
POST_EVENT_DURATION = 20  # seconds to buffer after incident

FRAME_RATE = 20.0
FRAME_SIZE = (640, 480)

MQTT_TIMEOUT = 30  # seconds of silence before fallback
LOOP_RECORD_DURATION = 60 * 60  # seconds for continuous overwrite

# === Global State ===
incident_active = False
incident_resolved = False
last_received_data = {}
last_mqtt_time = time.time()


# === Utility Functions ===
def current_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_incident_video(pre_frames, post_frames):
    """Save a video clip with frames before and after the incident."""
    os.makedirs("incidents", exist_ok=True)
    filename = f"incident_{current_timestamp()}.mp4"
    filepath = os.path.join("incidents", filename)

    writer = cv2.VideoWriter(filepath, cv2.VideoWriter_fourcc(*'mp4v'), FRAME_RATE, FRAME_SIZE)
    for frame in pre_frames + post_frames:
        writer.write(frame)
    writer.release()

    print(f"\n Incident saved: {filepath}\n")


def archive_loop_video(writer):
    """Save and rotate the continuous recording loop."""
    writer.release()
    os.makedirs("continuous", exist_ok=True)

    new_path = f"continuous/loop_{current_timestamp()}.mp4"
    os.rename("loop_record.mp4", new_path)

    print(f" Continuous loop saved: {new_path}")


def detect_camera(index_limit=5):
    """Try to find and return the index of a working webcam."""
    for i in range(index_limit):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"🎥 Camera {i} is working.")
            cap.release()
            return i
        else:
            print(f"❌ Camera {i} is not available.")
            cap.release()
    print("🚫 No working camera found.")
    return None



# === MQTT Callbacks ===
def handle_mqtt_message(client, userdata, message):
    global incident_active, incident_resolved, last_received_data, last_mqtt_time
    last_mqtt_time = time.time()

    try:
        if not message.payload:
            return

        data = json.loads(message.payload.decode())
        speed = data.get("speed", 0)
        last_received_data = data

        if speed > SPEED_LIMIT:
            if not incident_active:
                print(f"\n High speed detected ({speed:.2f} km/h). Incident triggered.")
            incident_active = True
            incident_resolved = False
        else:
            if incident_active and not incident_resolved:
                print(f"\n Speed normalized ({speed:.2f} km/h). Starting post-incident timer.")
                incident_resolved = True

    except json.JSONDecodeError:
        print(" Invalid JSON payload.")
    except Exception as e:
        print(" MQTT processing error:", e)


def start_mqtt_client():
    client = mqtt.Client()
    client.on_message = handle_mqtt_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()


# === Fallback Watchdog ===
def mqtt_watchdog():
    global incident_resolved
    while True:
        time.sleep(5)
        if time.time() - last_mqtt_time > MQTT_TIMEOUT:
            if incident_active and not incident_resolved:
                print("\n MQTT silence detected — triggering post-incident.")
                incident_resolved = True


# === Main Monitoring Logic ===
def start_monitoring():
    global incident_active, incident_resolved

    cam_index = detect_camera()
    if cam_index is None:
        return

    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_SIZE[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_SIZE[1])
    cap.set(cv2.CAP_PROP_FPS, FRAME_RATE)

    loop_writer = cv2.VideoWriter("loop_record.mp4", cv2.VideoWriter_fourcc(*'mp4v'), FRAME_RATE, FRAME_SIZE)
    loop_start_time = time.time()

    pre_event_buffer = deque(maxlen=int(PRE_EVENT_DURATION * FRAME_RATE))
    post_event_frames = []
    post_timer_started = False
    post_timer_start_time = None

    print(" Camera monitoring started... Press 's' to stop.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print(" Frame read failed.")
                break

            loop_writer.write(frame)
            pre_event_buffer.append(frame)

            # Rotate loop video
            if time.time() - loop_start_time >= LOOP_RECORD_DURATION:
                archive_loop_video(loop_writer)
                loop_writer = cv2.VideoWriter("loop_record.mp4", cv2.VideoWriter_fourcc(*'mp4v'), FRAME_RATE, FRAME_SIZE)
                loop_start_time = time.time()
                print(" Continuous loop restarted.")

            # Show live feed (for dev/debug)
            cv2.imshow("Live Feed", frame)
            if cv2.waitKey(1) & 0xFF == ord('s'):
                break

            # Incident recording logic
            if incident_active:
                post_event_frames.append(frame)

                if incident_resolved:
                    if not post_timer_started:
                        post_timer_start_time = time.time()
                        post_timer_started = True

                    elif time.time() - post_timer_start_time >= POST_EVENT_DURATION:
                        print(" Saving incident clip...")
                        save_incident_video(list(pre_event_buffer), post_event_frames)

                        # Reset
                        incident_active = False
                        incident_resolved = False
                        post_timer_started = False
                        post_event_frames.clear()

    except KeyboardInterrupt:
        print("\n Interrupted by user.")

    finally:
        cap.release()
        archive_loop_video(loop_writer)
        cv2.destroyAllWindows()
        print("Cleaned up resources.")


# === Program Entry Point ===
if __name__ == "__main__":
    start_mqtt_client()
    threading.Thread(target=mqtt_watchdog, daemon=True).start()
    start_monitoring()

