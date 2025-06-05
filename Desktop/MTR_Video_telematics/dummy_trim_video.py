import cv2
import datetime
import os
import time
from collections import deque
 
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
    print(f"🎯 Incident clip saved: {filepath}")
 
def continuous_recording(camera_index=0, resolution=(640, 480), fps=20.0):
    print("🎥 Starting smart recording...")
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
 
    if not cap.isOpened():
        print("❌ Error: Could not open camera.")
        return
 
    # Setup directories and rolling buffer

    save_dir = "/home/csg/Video_telematics/continuous"
    os.makedirs(save_dir, exist_ok=True)
    cont_filename = f"continuous_recording_{get_timestamp()}.mp4"
    cont_filepath = os.path.join(save_dir, cont_filename)
    cont_writer = cv2.VideoWriter(cont_filepath, cv2.VideoWriter_fourcc(*'mp4v'), fps, resolution)
    buffer_seconds = 15
    buffer_size = int(fps * buffer_seconds)
    frame_buffer = deque(maxlen=buffer_size)
 
    try:

        while True:

            ret, frame = cap.read()

            if not ret:

                print("⚠️ Failed to grab frame.")

                break
 
            # Write to continuous file

            cont_writer.write(frame)
 
            # Add to rolling buffer

            frame_buffer.append(frame)
 
            # Brightness check

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            brightness = gray.mean()

            if brightness < 50:

                print(f"🌑 Low visibility detected! Brightness: {brightness:.2f}")

                print("⏳ Capturing incident clip...")
 
                # Capture 15 sec after this point

                post_frames = []

                start_time = time.time()

                while time.time() - start_time < buffer_seconds:

                    ret2, post_frame = cap.read()

                    if not ret2:

                        break

                    cont_writer.write(post_frame)

                    post_frames.append(post_frame)

                    cv2.imshow('Recording (press s to stop)', post_frame)

                    if cv2.waitKey(1) & 0xFF == ord('s'):

                        raise KeyboardInterrupt()
 
                # Save the clip (15s before + 15s after)

                save_incident_clip(list(frame_buffer), post_frames, resolution)
 
            # Live preview

            cv2.imshow('Recording (press s to stop)', frame)

            if cv2.waitKey(1) & 0xFF == ord('s'):

                print("🛑 's' pressed. Stopping recording.")

                break
 
    except KeyboardInterrupt:

        print("🛑 Recording stopped manually.")
 
    finally:

        cap.release()

        cont_writer.release()

        cv2.destroyAllWindows()

        print(f"✅ Continuous video saved to: {cont_filepath}")
 
if __name__ == "__main__":

    continuous_recording(camera_index=0)  # Try 0, 1, 2 if 3 doesn't work

 
