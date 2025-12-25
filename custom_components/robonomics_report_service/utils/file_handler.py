import logging
import os
import tempfile
import random
import shutil
from typing import Optional, List
from os.path import isdir

from ..const import LOGS_MAX_LEN
from .encrypt_tools import multi_device_encrypt_message

_LOGGER = logging.getLogger(__name__)

def create_temp_dir_with_encrypted_files(
    dirname: str,
    files: List[str],
    sender_seed: Optional[str],
    receiver_address: Optional[str],
) -> str:
    """Create directory in tepmoral directory and copy there files.

    :param dirname: the name of the directory to create
    :param files: list of file pathes to copy

    :return: path to the created directory
    """
    try:
        temp_dirname = tempfile.gettempdir()
        dirpath = f"{temp_dirname}/{dirname}"
        _LOGGER.debug("Start creating tempdir %s", dirpath)
        if os.path.exists(dirpath):
            dirpath += str(random.randint(1, 1000))
        try:
            os.mkdir(dirpath)
        except Exception as e:
            _LOGGER.warning("Can't create tempdir: %s, retrying...", e)
            return create_temp_dir_with_encrypted_files(dirname, files, sender_seed, receiver_address)
        for filepath in files:
            filename = filepath.split("/")[-1]
            if sender_seed and receiver_address:
                with open(filepath, "r") as f:
                    data = f.read()
                data = data[-LOGS_MAX_LEN:]
                encrypted_data = multi_device_encrypt_message(
                    data, sender_seed, receiver_address
                )
                with open(f"{dirpath}/{filename}", "w") as f:
                    f.write(encrypted_data)
            else:
                shutil.copyfile(filepath, f"{dirpath}/{filename}")
        return dirpath
    except Exception as e:
        _LOGGER.error(f"Exception in create temp dir: {e}")


def delete_temp_dir(dirpath: str) -> None:
    """
    Delete temporary directory

    :param dirpath: the path to the directory
    """
    shutil.rmtree(dirpath)

def get_tempdir_filenames(dirname_prefix: str) -> List[str]:
    temp_dirname = tempfile.gettempdir()
    filenames = os.listdir(temp_dirname)
    temdir_names = []
    for filename in filenames:
        filepath = f"{temp_dirname}/{filename}"
        if isdir(filepath) and filename.startswith(dirname_prefix):
            temdir_names.append(filepath)
    return temdir_names
