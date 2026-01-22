import os
from pathlib import Path
from typing import cast

from robonomicsinterface import Account

from custom_components.robonomics_report_service.utils import file_handler

def test_create_temp_dir_with_encrypted_files(
        tmp_path,
        monkeypatch,
        temp_dir_name_prefix
    ):
    """Test encrypting the whole directory with files"""

    # Fake tempfile function to use temp dir from PyTest
    def fake_mkdtemp(prefix):
        fake_tmp_dir_path = tmp_path / (prefix + "-fixed")
        fake_tmp_dir_path.mkdir()
        return str(fake_tmp_dir_path)
    monkeypatch.setattr(file_handler.tempfile, "mkdtemp", fake_mkdtemp)

    # No need to test encryption again
    monkeypatch.setattr(
        file_handler,
        "multi_envelope_encrypt_data",
        lambda *args, **kwargs: "ENCRYPTED"
    )

    sender_account = cast(Account, object())

    test_files = []
    for i in range(1, 6):
        test_file = tmp_path / f"test_file_{i}.log"
        test_file.write_text(f"test message {i}", encoding="utf-8")
        test_files.append(str(test_file))

    test_temp_dir_path = file_handler.create_temp_dir_with_encrypted_files(
        temp_dir_name_prefix,
        test_files,
        sender_account=sender_account,
        recipient_addresses=["addr"]
    )

    test_temp_dir = Path(test_temp_dir_path)
    assert test_temp_dir.exists()

    file_number = 0
    with os.scandir(test_temp_dir) as all_temp_files:
        for temp_file in all_temp_files:

            file = Path(temp_file.path)
            assert file.read_text(encoding="utf-8") == "ENCRYPTED"
            assert file.suffix == ".enc"

            file_number += 1
    assert file_number == len(test_files)

def test_delete_temp_dir(tmp_path, temp_dir_name_prefix):
    """Test deleting temp dir with files"""
    temp_dir_path = tmp_path / (temp_dir_name_prefix + "-fixed")
    temp_dir_path.mkdir()
    test_file = temp_dir_path / "test_file.log"
    test_file.write_text("test message", encoding="utf-8")

    file_handler.delete_temp_dir(str(temp_dir_path))
    assert not temp_dir_path.exists()

def test_get_temp_dirs(tmp_path, monkeypatch, temp_dir_name_prefix):
    """Test collecting list of temp dirs"""
    monkeypatch.setattr(
        file_handler.tempfile,
        "gettempdir",
        lambda: str(tmp_path)
    )

    temp_dirs_paths = []

    for i in range(1, 6):
        temp_dir_path = tmp_path / (f"{temp_dir_name_prefix}-{i}")
        temp_dir_path.mkdir()
        temp_dirs_paths.append(str(temp_dir_path))

    other_dir_path = tmp_path / "other-1"
    other_dir_path.mkdir()

    found_temp_dirs_paths = file_handler.get_temp_dirs(temp_dir_name_prefix)

    assert str(other_dir_path) not in found_temp_dirs_paths
    assert sorted(temp_dirs_paths) == sorted(found_temp_dirs_paths)
