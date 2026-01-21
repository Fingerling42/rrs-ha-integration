import logging
import os
import tempfile
import shutil

from robonomicsinterface import Account

from ..const import LOGS_MAX_LEN
from .encrypt_tools import multi_envelope_encrypt_data

_LOGGER = logging.getLogger(__name__)

def create_temp_dir_with_encrypted_files(
    dir_name_prefix: str,
    file_paths: list[str],
    sender_account: Account,
    recipient_addresses: list[str],
) -> str:
    """
    Create directory in tepmoral directory and copy there files.

    :param dir_name_prefix:     the name of the directory to create
    :param file_paths:          list of file paths to copy
    :param sender_account:      Robonomics account of sender
    :param recipient_addresses: list of addresses to send encrypted files

    :return: path to the created directory
    """
    # Create unique temp directory (ensured by mkdtemp)
    temp_dir_path = tempfile.mkdtemp(prefix=dir_name_prefix + "-")
    _LOGGER.debug("Tempdir %s is created", temp_dir_path)

    # Encrypt each file and copy it to temp directory
    written = 0
    for file_path in file_paths:
        try:
            # Prepere metadata with file name
            file_name = os.path.basename(file_path)
            metadata = {
                "orig_file_name": file_name
            }

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()

            # Only last 3 MiB of symbols are needed
            data = data[-LOGS_MAX_LEN:]

            encrypted_data = multi_envelope_encrypt_data(
                data,
                sender_account,
                list(recipient_addresses),
                metadata
            )

            # Unique temp file with ecncypted data
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".enc",
                dir=temp_dir_path,
                delete=False,
                delete_on_close=False
            ) as f:
                f.write(encrypted_data)
            written += 1

        except OSError:
            _LOGGER.warning(
                "Failed to read/write file for encryption %s",
                file_path
            )
        except Exception:
            _LOGGER.exception("Unexpected error while encrypting %s", file_path)

    if written == 0:
        _LOGGER.error("No files were encrypted; aborting")
        raise ValueError("Failed to create any encrypted files")

    _LOGGER.debug("Encrypted %d from %d files", written, len(file_paths))

    return temp_dir_path

def delete_temp_dir(temp_dir_path: str) -> None:
    """
    Delete temporary directory

    :param dirpath: the path to the directory
    """
    try:
        shutil.rmtree(temp_dir_path)
        _LOGGER.debug("Tempdir removed: %s", temp_dir_path)
    except FileNotFoundError:
        _LOGGER.debug("Tempdir already removed: %s", temp_dir_path)
    except Exception:
        _LOGGER.warning("Failed to remove tempdir: %s", temp_dir_path)

def get_temp_dirs(dir_name_prefix: str) -> list[str]:
    """
    Collect list with all created temp dirs

    :param dir_name_prefix: Prefix of temp dirs
    :return: List with paths of temp dirs
    """
    main_temp_dir_path = tempfile.gettempdir()
    found_temp_dirs_paths: list[str] = []

    try:
        with os.scandir(main_temp_dir_path) as all_temp_files:
            for temp_file in all_temp_files:
                if (
                    temp_file.is_dir()
                    and temp_file.name.startswith(dir_name_prefix)
                ):
                    found_temp_dirs_paths.append(temp_file.path)
    except OSError:
        _LOGGER.warning("Failed to scan temp dir: %s", main_temp_dir_path)
        return []

    return found_temp_dirs_paths
