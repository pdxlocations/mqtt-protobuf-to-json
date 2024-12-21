'''
Powered by Meshtastic.org
'''

import paho.mqtt.client as mqtt
import os, json, logging, time, sys, re
from meshtastic.protobuf import mqtt_pb2, portnums_pb2
from meshtastic import protocols
from encryption import decrypt_packet

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Adjust level as needed (DEBUG for more detailed output)
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Get the directory where the script is located to build the path for the config file
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, 'config.json')

# Load configuration from the config.py file
config = {}
if os.path.exists(config_path):
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
else:
    raise FileNotFoundError(f"Configuration file not found: {config_path}")

# Extract necessary config values
broker = config['broker']['address']
port = config['broker']['port']
user = config['broker']['user']
password = config['broker']['password']
buf_topic = config['broker']['buftopic']
json_topic = config['broker']['jsontopic']
channel = config['broker']['buftopic']
channel_name = config['channel']['name']
key = config['channel']['key']
key = "1PG7OiApB1nwvP+rz05pAQ==" if key == "AQ==" else key

def create_mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(user, password)
    logging.info(f"Connecting to broker at {broker}:{port}...")
    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        print(f"Failed to connect to broker: {e}")
        sys.exit(1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.loop_forever()
    return client

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        logging.info("Connected to broker successfully")
        client.subscribe(buf_topic + "/#")
        logging.info(f"Subscribed to topic: {buf_topic}")
    else:
        logging.error(f"Failed to connect with reason code {reason_code}")


def parse_payload(payload_str):
    """Parses the payload string into a dictionary, including nested fields."""
    try:
        payload_dict = {}
        current_key = None
        nested_dict = {}

        for line in payload_str.splitlines():
            # Match key-value pairs with numeric or string values
            match = re.match(r"(\w+):\s(.+)", line)
            if match:
                key, value = match.groups()
                try:
                    # Attempt to convert to float or int; fallback to string
                    if "." in value or "e" in value.lower():
                        payload_dict[key] = float(value)
                    else:
                        payload_dict[key] = int(value)
                except ValueError:
                    payload_dict[key] = value.strip('"')  # Remove surrounding quotes for strings

            # Match the start of a nested structure
            elif re.match(r"(\w+)\s{", line):
                current_key = line.strip(" {")
                nested_dict = {}

            # Match key-value pairs inside a nested structure
            elif re.match(r"\s+(\w+):\s(.+)", line):
                nested_match = re.match(r"\s+(\w+):\s(.+)", line)
                if nested_match:
                    nested_key, nested_value = nested_match.groups()
                    try:
                        if "." in nested_value or "e" in nested_value.lower():
                            nested_dict[nested_key] = float(nested_value)
                        else:
                            nested_dict[nested_key] = int(nested_value)
                    except ValueError:
                        nested_dict[nested_key] = nested_value.strip('"')

            # Match the end of a nested structure
            elif line.strip() == "}":
                if current_key:
                    payload_dict[current_key] = nested_dict
                    current_key = None

        return payload_dict
    except Exception as e:
        logging.error(f"Failed to parse payload: {e}")
        return None
    
def get_portnum_name(portnum) -> str:
    """For Logging: Retrieve the name of the port number from the protobuf enum."""
    try:
        return portnums_pb2.PortNum.Name(portnum)  # Use protobuf's enum name lookup
    except ValueError:
        return f"Unknown ({portnum})"  # Handle unknown port numbers gracefully


def format_mac_address(raw_mac):
    """Format a raw escaped MAC address string into a standard format."""
    try:
        # Convert the raw escaped string to bytes
        mac_bytes = bytes(raw_mac, "utf-8").decode("unicode_escape").encode("latin1")
        # Format the bytes into a MAC address (e.g., AA:BB:CC:DD:EE:FF)
        formatted_mac = ":".join(f"{b:02X}" for b in mac_bytes)
        return formatted_mac
    except Exception as e:
        logging.error(f"Failed to format MAC address: {e}")
        return raw_mac  # Return the original raw string if formatting fails
    

def on_message(client, userdata, msg):
    se = mqtt_pb2.ServiceEnvelope()  # Main variable for parsing and decoding
    try:
        se.ParseFromString(msg.payload)
        mp = se.packet

    except Exception as e:
        print(f"*** ServiceEnvelope: {str(e)}")
        return
    
    # Decrypt the payload if necessary
    if mp.HasField("encrypted") and not mp.HasField("decoded"):
        decoded_data = decrypt_packet(mp, key)
        if decoded_data is None:  # Check if decryption failed
            logging.error("Decryption failed; skipping message")
            return  # Skip processing this message if decryption failed
    else:
        decoded_data = mp.decoded
    
    mp.decoded.CopyFrom(decoded_data)

    portNumInt = mp.decoded.portnum
    handler = protocols.get(portNumInt)
    
    # Check if a valid handler exists
    if handler is not None and handler.protobufFactory is not None:
        payload = handler.protobufFactory()
        payload.ParseFromString(mp.decoded.payload)
    else:
        logging.warning(f"No handler found for portNumInt: {portNumInt}")
        payload = None  # Set payload to None if no handler exists

    if payload:
        payload = str(payload)
        mp.decoded.payload = payload.encode("utf-8")

    portnum_type = get_portnum_name(mp.decoded.portnum)


    # Extracting and formatting data into JSON
    try:
        raw_payload = getattr(mp.decoded, "payload", b"").decode('utf-8')
        structured_payload = parse_payload(raw_payload)

        if "macaddr" in structured_payload:
            structured_payload["macaddr"] = format_mac_address(structured_payload["macaddr"])

        message_dict = {
            "channel": mp.channel,
            "from": getattr(mp, "from", None),
            "hop_start": mp.hop_start,
            "hops_away": mp.hop_start - (mp.hop_start - mp.hop_limit),
            "id": mp.id,
            "payload": structured_payload,
            "rssi": mp.rx_rssi,
            "sender": msg.topic.split('/')[-1],
            "snr": mp.rx_snr,
            "timestamp": mp.rx_time,
            "to": mp.to,
            "type": portnum_type
        }

        # Add optional fields if available
        if mp.decoded.HasField("bitfield"):
            message_dict["decoded"]["bitfield"] = mp.decoded.bitfield

        # Serialize the message dictionary to a JSON string
        json_message = json.dumps(message_dict, indent=4)
        logging.info(f"JSON message: \n{json_message}")
        
        # Publish message to the JSON topic
        publish_topic = json_topic + "/" + channel_name + "/" + msg.topic.split('/')[-1]
        client.publish(publish_topic, json_message)

    except Exception as e:
        logging.error(f"Failed to process message: {e}")



def main():
    create_mqtt_client()
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()