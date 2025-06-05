import random
import time
import math
import cv2
import os
from collections import deque
import datetime
import threading

# Simulated Vehicle Publisher Code (Publisher)
class SimulatedVehicle:
    def __init__(self, x=0, y=0, velocity=0):
        self.x = x
        self.y = y
        self.velocity = velocity
        self.angle = 0  # Direction in degrees

    def move(self, acceleration, dt):
        self.velocity += acceleration * dt
        dx = self.velocity * math.cos(math.radians(self.angle)) * dt
        dy = self.velocity * math.sin(math.radians(self.angle)) * dt
        self.x += dx
        self.y += dy
        return self.x, self.y, self.velocity

    def detect_crash(self):
        return random.random() < 0.05  # 5% chance of incident


class Publisher:
    def __init__(self, subscriber):
        self.vehicle = SimulatedVehicle()
        self.subscriber = subscriber

    def start_publishing(self):
        while True:
            x, y, speed = self.vehicle.move(acceleration=0.5, dt=0.1)
            print(f"Location: ({x:.2f}, {y:.2f}), Speed: {speed:.2f} m/s")

            if self.vehicle.detect_crash():
                print("🚨 Incident detected! Sending to subscriber...")
                self.subscriber.handle_incident(x, y, speed)

            time.sleep(0.1)

# Video saving utility
def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def save_incident_clip(pre_frames, post_frames, resolution, fps=20.0):
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
    print(f"🚨 Incident saved: {filepath}")


# Subscriber (video capture & incident handler)
class Subscriber:
    def __init__(self, camera_index=1, resolution=(640, 480), fps=20.0):
        self.camera_index = camera_index
        self.resolution = resolution
        self.fps = fps
        self.buffer_time = 3 * 60  # 3 minutes buffer
        self.frame_buffer = deque(maxlen=int(self.buffer_time * fps))
        self.cap = cv2.VideoCapture(self.camera_index)
        self.lock = threading.Lock()

        if not self.cap.isOpened():
            print("❌ Could not open camera.")
            self.cap = None

    def handle_incident(self, x, y, speed):
        if self.cap is None:
            print("⚠️ Incident skipped: camera not available.")
            return

        try:
            print(f"🚨 Incident occurred at Location: ({x}, {y}), Speed: {speed} m/s")
            pre_frames = list(self.frame_buffer)
            post_frames = self.capture_post_incident()
            save_incident_clip(pre_frames, post_frames, self.resolution, self.fps)
        except Exception as e:
            print(f"❌ Exception during incident handling: {e}")

    def capture_post_incident(self):
        post_frames = []
        start_time = time.time()
        while time.time() - start_time < 15:  # 15 seconds after incident
            with self.lock:
                ret, frame = self.cap.read()
            if not ret:
                print("❌ Failed to capture post-incident frame.")
                break
            self.frame_buffer.append(frame)
            post_frames.append(frame)
        return post_frames
    def start_recording(self):
        if self.cap is None:
            return

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter("continuous_video1.mp4", fourcc, self.fps, self.resolution)

        while True:
            with self.lock:
                ret, frame = self.cap.read()
            if not ret:
                print("❌ Error reading frame.")
                break

            self.frame_buffer.append(frame)
            video_writer.write(frame)

            cv2.imshow("Continuous Video Feed", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        video_writer.release()
        cv2.destroyAllWindows()


# Main function
def main():
    subscriber = Subscriber(camera_index=0)
    publisher = Publisher(subscriber)

    publisher_thread = threading.Thread(target=publisher.start_publishing)
    publisher_thread.daemon = True
    publisher_thread.start()

    subscriber.start_recording()


if __name__ == "__main__":
    main()

