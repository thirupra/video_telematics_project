import subprocess
import datetime
import os
import fcntl
import time
import signal

def is_camera_available(dev="/dev/video3"):
    try:
        with open(dev, 'rb') as cam:
            fcntl.flock(cam, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(cam, fcntl.LOCK_UN)
        return True
    except (OSError, IOError):
        return False

def record_video(duration=20, dev="/dev/video3"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"/home/csg/video_{timestamp}.mp4"
    print(f"Recording video: {output_file}")

    try:
        subprocess.run([
            "ffmpeg",
            "-f", "v4l2",
            "-i", dev,
            "-t", str(duration),
            output_file
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed: {e}")
    finally:
        print(f"Finished recording: {output_file}")

def continuous_recording():
    print("Starting continuous video recording...")
    
    while True:
        if not is_camera_available():
            print("Camera is busy. Waiting 5 seconds before retrying...")
            time.sleep(5)  # Wait before checking again
            continue  # Retry if the device is busy

        record_video()  # Record video in chunks of 10 seconds 
        time.sleep(1)  # Pause for a second before starting the next recording

if __name__ == "__main__":
    continuous_recording()

