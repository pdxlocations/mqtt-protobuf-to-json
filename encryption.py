import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from meshtastic.protobuf import mesh_pb2
import logging

def decrypt_packet(mp, key):
    """Decrypt the encrypted message payload and return the decoded data."""
    try:
        key_bytes = base64.b64decode(key.encode('ascii'))

        # Build the nonce from message ID and sender
        nonce_packet_id = getattr(mp, "id").to_bytes(8, "little")
        nonce_from_node = getattr(mp, "from").to_bytes(8, "little")
        nonce = nonce_packet_id + nonce_from_node

        # Decrypt the encrypted payload
        cipher = Cipher(algorithms.AES(key_bytes), modes.CTR(nonce), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_bytes = decryptor.update(getattr(mp, "encrypted")) + decryptor.finalize()

        # Parse the decrypted bytes into a Data object
        data = mesh_pb2.Data()
        data.ParseFromString(decrypted_bytes)
        return data

    except Exception as e:
        logging.error(f"Failed to decrypt: {e}")
        return None
