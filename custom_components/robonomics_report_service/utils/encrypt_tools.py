import logging
import json
from typing import Union

from robonomicsinterface import Account
from substrateinterface import Keypair, KeypairType

_LOGGER = logging.getLogger(__name__)

def multi_device_encrypt_message(message, sender_seed: str, recipient_address: str) -> str:
    try:
        random_seed = Keypair.generate_mnemonic()
        random_acc = Account(random_seed, crypto_type=KeypairType.ED25519)
        sender_acc = Account(sender_seed, crypto_type=KeypairType.ED25519)
        sender_keypair = sender_acc.keypair
        encrypted_data = encrypt_message(
            str(message), sender_keypair, random_acc.keypair.public_key
        )
        devices = [recipient_address, sender_acc.get_address()]
        encrypted_keys = {}
        # _LOGGER.debug(f"Encrypt states for following devices: {devices}")
        for device in devices:
            try:
                receiver_kp = Keypair(
                    ss58_address=device, crypto_type=KeypairType.ED25519
                )
                encrypted_key = encrypt_message(
                    random_seed, sender_keypair, receiver_kp.public_key
                )
                encrypted_keys[device] = encrypted_key
            except Exception as e:
                _LOGGER.warning(
                    f"Faild to encrypt key for: {device} with error: {e}. Check your RWS devices, you may have SR25519 address in devices."
                )
        encrypted_keys["data"] = encrypted_data
        data_final = json.dumps(encrypted_keys)
        return data_final
    except Exception as e:
        _LOGGER.error(f"Exception in encrypt for devices: {e}")

def encrypt_message(
    message: Union[bytes, str],
    sender_keypair: Keypair,
    recipient_public_key: bytes,
) -> str:
    """Encrypt message with sender private key and recipient public key

    :param message: Message to encrypt
    :param sender_keypair: Sender account Keypair
    :param recipient_public_key: Recipient public key

    :return: encrypted message
    """
    encrypted = sender_keypair.encrypt_message(message, recipient_public_key)
    return f"0x{encrypted.hex()}"

def decrypt_message(encrypted_message: str, receiver_seed: str, sender_address: str) -> str:
    recipient_acc = Account(receiver_seed, crypto_type=KeypairType.ED25519)
    sender_kp = Keypair(ss58_address=sender_address)
    try:
        data_json = json.loads(encrypted_message)
    except:
        return _decrypt_message(encrypted_message, sender_kp.public_key, recipient_acc.keypair).decode("utf-8")
    try:
        if recipient_acc.get_address() in data_json:
            decrypted_seed = _decrypt_message(
                data_json[recipient_acc.get_address()],
                sender_kp.public_key,
                recipient_acc.keypair,
            ).decode("utf-8")
            decrypted_acc = Account(decrypted_seed, crypto_type=KeypairType.ED25519)
            decrypted_data = _decrypt_message(
                data_json["data"], sender_kp.public_key, decrypted_acc.keypair
            ).decode("utf-8")
            return decrypted_data
        else:
            _LOGGER.error(f"Error in decrypt for devices: account is not in devices")
    except Exception as e:
        _LOGGER.error(f"Exception in decrypt for devices: {e}")

def _decrypt_message(
    encrypted_message: str,
    sender_public_key: bytes = None,
    recipient_keypair: Keypair = None,
) -> bytes:
    """Decrypt message with recepient private key and sender puplic key

    :param encrypted_message: Message to decrypt
    :param sender_public_key: Sender public key
    :param recipient_keypair: Recepient account keypair

    :return: Decrypted message
    """
    if encrypted_message[:2] == "0x":
        encrypted_message = encrypted_message[2:]
    bytes_encrypted = bytes.fromhex(encrypted_message)

    return recipient_keypair.decrypt_message(bytes_encrypted, sender_public_key)