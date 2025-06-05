# simulator.py
import time
import random
import json
import paho.mqtt.client as mqtt

broker = "localhost"
topic = "vehicle/data"
client = mqtt.Client()
client.connect(broker, 1883, 60)

def simulate_data():
    while True:
        # Normal data
        lat = 12.97 + random.uniform(-0.01, 0.01)
        lon = 77.59 + random.uniform(-0.01, 0.01)
        speed = random.uniform(30, 80)

        # Inject random incident
        if random.random() < 0.05:  # 5% chance
            speed = random.uniform(130, 160)  # high-speed incident

        payload = json.dumps({
            "latitude": lat,
            "longitude": lon,
            "speed": speed
        })

        client.publish(topic, payload)
        print("Published:", payload)
        time.sleep(2)

if __name__ == "__main__":
    simulate_data()

