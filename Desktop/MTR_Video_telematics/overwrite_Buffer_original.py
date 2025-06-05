import cv2
import os
import time
from collections import deque
import datetime

def find_working_camera_index(max_index=5):
    for index in range(max_index):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            cap.release()
            print(f"✅ Using camera index: {index}")
            return index
        cap.release()
    print("❌ No available camera found.")
    return None

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def save_incident_clip(pre_frames, incident_frames, post_frames, resolution, fps=20.0):
    save_dir = "/home/csg/Video_telematics/incidents"
    os.makedirs(save_dir, exist_ok=True)
    filename = f"incident_{get_timestamp()}.mp4"
    filepath = os.path.join(save_dir, filename)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filepath, fourcc, fps, resolution)

    for frame in pre_frames:
        out.write(frame)
    for frame in incident_frames:
        out.write(frame)
    for frame in post_frames:
        out.write(frame)

    out.release()
    print(f"🚨 Incident saved: {filepath}")

def continuous_with_incident(camera_index=0, resolution=(640, 480), fps=20.0):
    loop_duration_minutes = 3
    pre_incident_seconds = 15
    post_incident_seconds = 15

    loop_duration_seconds = loop_duration_minutes * 60
    pre_buffer_size = int(pre_incident_seconds * fps)

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

    frame_buffer = deque(maxlen=pre_buffer_size)
    incident_frames = []
    post_frames = []
    loop_start_time = time.time()

    recording_incident = False
    post_recording = False
    post_record_start_time = None

    print("🎥 Recording started. 3-min loop + incident capture ready...")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Frame capture failed.")
                break

            # Always save into loop video
            writer.write(frame)

            # Always maintain pre-incident buffer
            frame_buffer.append(frame)

            # Overwrite after 3 minutes
            if time.time() - loop_start_time >= loop_duration_seconds:
                writer.release()
                writer = cv2.VideoWriter(loop_file_path, fourcc, fps, resolution)
                loop_start_time = time.time()
                print("🔁 Overwriting 3-minute loop recording...")

            # Check brightness
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = gray.mean()

            # Check for low brightness (incident)
            if brightness < 50 and len(frame_buffer) == pre_buffer_size:
                if not recording_incident:
                    print(f"🌑 Low brightness detected ({brightness:.2f}) — starting incident recording...")
                    recording_incident = True
                    incident_frames = []

                incident_frames.append(frame)

            elif recording_incident and brightness >= 50:
                if not post_recording:
                    print("🌕 Brightness normal — starting post-incident recording...")
                    post_recording = True
                    post_record_start_time = time.time()
                    post_frames = []

                post_frames.append(frame)

                # If post recording completed 15 seconds
                if time.time() - post_record_start_time >= post_incident_seconds:
                    save_incident_clip(list(frame_buffer), incident_frames, post_frames, resolution, fps)
                    recording_incident = False
                    post_recording = False
                    incident_frames = []
                    post_frames = []

            # If incident ongoing (low brightness), continue adding frames
            elif recording_incident:
                incident_frames.append(frame)

            # Show live
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
    camera_index = find_working_camera_index()
    if camera_index is not None:
        continuous_with_incident(camera_index=camera_index)

