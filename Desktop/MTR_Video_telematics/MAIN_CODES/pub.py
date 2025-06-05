# simulator.py
import time
import random
import json
import paho.mqtt.client as mqtt

broker = "localhost"
topic = "vehicle/data" #Data is published to this topic 
client = mqtt.Client() #Creating MQTT client 
client.connect(broker, 1883, 60) #Connecting to the broker onport 1883 with a 60 second keep-alive timeout 

def simulate_data():
    while True: #Starting a loop to continuously generate and publish data 
        # Normal data
        #Generating  mock GPS coordinates(lat,long) and speed between 30-80km/h
        lat = 12.97 + random.uniform(-0.01, 0.01)
        lon = 77.59 + random.uniform(-0.01, 0.01)
        speed = random.uniform(30, 80)

        # Inject random incident
        if random.random() < 0.05:  # 5% chance
            speed = random.uniform(130, 160)  # high-speed incident
        
        #Encoding the telemetry as a JSON string.
        payload = json.dumps({
            "latitude": lat,
            "longitude": lon,
            "speed": speed
        })

        #Publishes the data to the MQTT topic and printing msg to the console 
        client.publish(topic, payload)
        print("Published:", payload)
        #waiting 1 sec before the next message 
        time.sleep(1)

if __name__ == "__main__":
    simulate_data()

