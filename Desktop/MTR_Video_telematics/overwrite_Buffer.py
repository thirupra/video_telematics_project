import cv2
import os
import time
from collections import deque
import datetime

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def save_incident_clip(pre_frames, post_frames, resolution, fps=20.0):
    save_dir = "/home/csg/Video_telematics/incidents"
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

def continuous_with_incident(camera_index=0, resolution=(640, 480), fps=20.0):
    # Settings
    loop_duration_minutes = 5
    incident_buffer_seconds = 15

    loop_duration_seconds = loop_duration_minutes * 60
    max_loop_frames = int(loop_duration_seconds * fps)
    buffer_size = int(incident_buffer_seconds * fps)

    # Setup
    save_dir = "/home/csg/Video_telematics/continuous"
    os.makedirs(save_dir, exist_ok=True)
    loop_file_path = os.path.join(save_dir, "loop_record.mp4")

    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
    cap.set(cv2.CAP_PROP_FPS, fps)

    if not cap.isOpened():
        print("❌ Could not open camera.")
        return

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(loop_file_path, fourcc, fps, resolution)

    frame_buffer = deque(maxlen=buffer_size)
    loop_start_time = time.time()

    print("🎥 Recording started. 3-min loop + 20s incident capture ready...")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Frame capture failed.")
                break

            # Write to loop file
            writer.write(frame)

            # Add to pre-incident buffer
            frame_buffer.append(frame)

            # Check for overwrite after 5 mins
            if time.time() - loop_start_time >= loop_duration_seconds:
                writer.release()
                writer = cv2.VideoWriter(loop_file_path, fourcc, fps, resolution)
                loop_start_time = time.time()
                print("🔁 Overwriting 3-minute loop recording...")

            # Check for incident (example: low brightness)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = gray.mean()
            if brightness < 50:
                print(f"🌑 Low brightness detected ({brightness:.2f}) — capturing incident...")

                post_frames = []
                post_start = time.time()
                while time.time() - post_start < incident_buffer_seconds:
                    ret2, post_frame = cap.read()
                    if not ret2:
                        break
                    writer.write(post_frame)
                    post_frames.append(post_frame)
                    cv2.imshow('Recording (press s to stop)', post_frame)
                    if cv2.waitKey(1) & 0xFF == ord('s'):
                        raise KeyboardInterrupt()

                # Save incident clip
                save_incident_clip(list(frame_buffer), post_frames, resolution, fps)

            # Show preview
            cv2.imshow('Recording (press s to stop)', frame)
            if cv2.waitKey(1) & 0xFF == ord('s'):
                print("🛑 Stopping recording.")
                break

    except KeyboardInterrupt:
        print("🛑 Manually interrupted.")

    finally:
        cap.release()
        writer.release()
        cv2.destroyAllWindows()
        print("✅ Camera and writer cleaned up.")

if __name__ == "__main__":
    continuous_with_incident(camera_index=0)

