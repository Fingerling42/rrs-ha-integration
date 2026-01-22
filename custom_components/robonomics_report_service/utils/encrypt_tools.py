import logging
import json
import secrets
from typing import Union, Optional, Any
from nacl.secret import SecretBox

from robonomicsinterface import Account
from substrateinterface import Keypair, KeypairType

_LOGGER = logging.getLogger(__name__)

def multi_envelope_encrypt_data(
    data: str,
    sender_account: Account,
    recipient_addresses: list[str],
    metadata: Optional[dict[str, Any]] = None,
) -> str:
    """
    Encrypt the data with a symmetric secret key, and then encrypt the key
    with asymmetric encryption for multiple recipients.

    :return: JSON structure with encrypted data and encypted secret keys
    """
    encryption_package = {}

    # Add metadata to encryption
    if metadata is not None:
        prepared_data = json.dumps(
            {"payload": data, "meta": metadata},
            ensure_ascii=False
        )
    else:
        prepared_data = data

    # Prepare encrypted data: bytes of data go through secret box,
    # resulted EncryptedMessage is serialised to hex
    secret_key = secrets.token_bytes(32)
    data_bytes = prepared_data.encode("utf-8")
    encrypted_data = SecretBox(secret_key).encrypt(data_bytes)
    encryption_package["data"] = "0x" + bytes(encrypted_data).hex()

    # Get unique recipient addresses and add sender public address to pool too
    addresses_for_encryption = set(recipient_addresses)
    addresses_for_encryption.add(sender_account.get_address())

    # Encrypt secret key for all addresses
    encryption_package["keys"] = {}

    for recipient_address in addresses_for_encryption:
        try:
            recipient_kp = Keypair(
                ss58_address=recipient_address,
                crypto_type=KeypairType.ED25519
            )

            encrypted_secret_key = encrypt_msg(
                secret_key,
                sender_account.keypair,
                recipient_kp.public_key
            )

            encryption_package["keys"][recipient_address] = encrypted_secret_key
        except Exception as e:
            _LOGGER.warning(
                "Failed to wrap secret key for recipient %s with error: %s",
                recipient_address, e)

    if not encryption_package["keys"]:
        _LOGGER.error("No recipients could be encrypted, aborting")
        raise ValueError("Failed to encrypt secret key for all recipients")

    return json.dumps(encryption_package)

def multi_envelope_decrypt_data(
    encryption_package: str,
    recipient_account: Account,
    sender_address: str,
) -> str:
    """
    Decrypt JSON structure with encrypted data: first decrypt the secret key
    (asymmetric), then use the secret key to decrypt the data itself.

    :return: data after decryption
    """

    # Check if JSON encryption package is valid
    try:
        package_json = json.loads(encryption_package)
    except json.JSONDecodeError as e:
        _LOGGER.warning("Envelope decrypt: invalid JSON package")
        raise ValueError("Invalid encryption package JSON") from e

    try:
        encrypted_secret_keys = package_json["keys"]
        encrypted_data_hex = package_json["data"]
    except (TypeError, ValueError) as e:
        _LOGGER.warning("Envelope decrypt: missing required fields in package")
        raise ValueError("Invalid encryption package structure") from e

    # Check if recipient address is authorized with secret key
    recipient_address = recipient_account.get_address()
    encrypted_secret_key = encrypted_secret_keys.get(recipient_address)
    if not encrypted_secret_key:
        _LOGGER.warning(
            "Envelope decrypt: recipient key not found for %s",
            recipient_address
        )
        raise ValueError("Recipient is not authorized for this package")

    # Get secret key from public-key decryption

    try:
        sender_kp = Keypair(
            ss58_address=sender_address,
            crypto_type=KeypairType.ED25519
        )

        secret_key = decrypt_msg(
            encrypted_secret_key,
            sender_kp.public_key,
            recipient_account.keypair
        )
    except Exception as e:
        _LOGGER.warning("Envelope decrypt: failed to unwrap secret key")
        raise ValueError("Failed to decrypt secret key") from e

    try:
        # Deserialize encrypted data: remove 0x from beginning,
        # transform to bytes
        encrypted_data = bytes.fromhex(encrypted_data_hex[2:])

        # Decrypt actual message (in form of bytes) and decode it
        decrypted_data_bytes = SecretBox(secret_key).decrypt(encrypted_data)
        decrypted_data = decrypted_data_bytes.decode("utf-8")

        return decrypted_data
    except Exception as e:
        _LOGGER.warning("Envelope decrypt: failed to decrypt payload")
        raise ValueError("Failed to decrypt payload") from e

def encrypt_msg(
    msg: Union[bytes, str],
    sender_keypair: Keypair,
    recipient_public_key: bytes,
) -> str:
    """Encrypt message with sender private key and recipient public key

    :param msg:                     Message to encrypt
    :param sender_keypair:          Sender account Keypair
    :param recipient_public_key:    Recipient public key

    :return: encrypted message
    """
    encrypted = sender_keypair.encrypt_message(msg, recipient_public_key)
    return f"0x{encrypted.hex()}"

def decrypt_msg(
    encrypted_msg: str,
    sender_public_key: bytes,
    recipient_keypair: Keypair,
) -> bytes:
    """
    Decrypt message with recepient private key and sender puplic key

    :param encrypted_msg:       Message to decrypt
    :param sender_public_key:   Sender public key
    :param recipient_keypair:   Recepient account keypair

    :return: Decrypted message
    """
    if encrypted_msg[:2] == "0x":
        encrypted_msg = encrypted_msg[2:]

    bytes_encrypted = bytes.fromhex(encrypted_msg)

    return recipient_keypair.decrypt_message(bytes_encrypted, sender_public_key)

def parse_decrypted(text: str) -> tuple[str, dict | None]:
    """
    Parse decrypted data if metadata was added or return just data overwise
    """
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "payload" in obj:
            return obj["payload"], obj.get("meta")
    except json.JSONDecodeError:
        pass
    return text, None
