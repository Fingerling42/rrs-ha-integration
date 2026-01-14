import pytest

from robonomicsinterface import Account
from substrateinterface import KeypairType

from custom_components.robonomics_report_service.utils.encrypt_tools import (
    encrypt_msg,
    decrypt_msg,
    multi_envelope_encrypt_data,
    multi_envelope_decrypt_data
)

SENDER_SEED = "frozen woman pet meat entire question balcony wing echo excess adjust sleep"
RECIPIENT_SEED = "lens exchange drum inside current bullet include stamp purity decline absurd play"

@pytest.fixture(name="sender_account")
def fixture_sender_account():
    """Returns sender account with ED25519 type"""
    return Account(SENDER_SEED, crypto_type=KeypairType.ED25519)

@pytest.fixture(name="recipient_account")
def fixture_recipient_account():
    """Returns recipient account with ED25519 type"""
    return Account(RECIPIENT_SEED, crypto_type=KeypairType.ED25519)

@pytest.mark.parametrize("msg", [
    b"",
    b"hello",
    b"\x00\x01\x02",
    "строка unicode 👍"
    ])
def test_round_trip_simple_msg(msg, sender_account, recipient_account):
    """Test encryption-decryption cycle for several msgs"""
    encrypted_msg = encrypt_msg(
        msg,
        sender_account.keypair,
        recipient_account.keypair.public_key
    )

    decrypted_msg = decrypt_msg(
        encrypted_msg,
        sender_account.keypair.public_key,
        recipient_account.keypair
    )

    expected_msg = msg.encode("utf-8") if isinstance(msg, str) else msg
    assert decrypted_msg == expected_msg

@pytest.mark.parametrize("data", [
    "",
    "hello",
    "\x00\x01\x02",
    "строка unicode 👍"
    ])
def test_round_trip_multi_envelope(data, sender_account, recipient_account):
    """Test encryption-decryption cycle for several msgs"""

    recipient_addresses = [recipient_account.get_address()]

    encrypted_data = multi_envelope_encrypt_data(
        data,
        sender_account,
        recipient_addresses
    )

    decrypted_data_recipient = multi_envelope_decrypt_data(
        encrypted_data,
        recipient_account,
        sender_account.get_address()
    )

    decrypted_data_sender = multi_envelope_decrypt_data(
        encrypted_data,
        sender_account,
        sender_account.get_address()
    )

    assert decrypted_data_recipient == decrypted_data_sender == data
