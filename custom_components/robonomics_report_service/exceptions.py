class RobonomicsReportServiceError(Exception):
    """Base exception for RRS integration."""


# for encrypt_tools.py
class EnvelopeRecipientEncryptError(RobonomicsReportServiceError):
    """Failed to encrypt envelop for a specific recipient address."""

    def __init__(self, address: str, reason: str | None = None) -> None:
        self.address = address
        msg = f"Failed to wrap secret key for recipient address: {address}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class EnvelopePackageDecryptError(RobonomicsReportServiceError):
    """
    Invalid envelope package (format/schema) or recipient key missing
    during decryption.
    """

    def __init__(self, msg: str, address: str | None = None) -> None:
        self.address = address
        full_msg = msg
        if address is not None:
            full_msg = f"{msg}: {address}"
        super().__init__(full_msg)


class EnvelopeCryptoDecryptError(RobonomicsReportServiceError):
    """Envelope crypto operation failed during decrypting."""

    def __init__(self, stage: str) -> None:
        self.stage = stage
        super().__init__(f"Envelope decrypt failed (stage={stage})")


# for file_handler.py
class EncryptedFilesStagingError(RobonomicsReportServiceError):
    """Failed to prepare encrypted files in temp directory."""

    def __init__(self, msg: str, file_path: str | None = None) -> None:
        self.file_path = file_path
        full_msg = msg
        if file_path is not None:
            full_msg = f"{msg}: {file_path}"
        super().__init__(full_msg)


class TempArchiveCreateError(RobonomicsReportServiceError):
    """Failed to create ZIP archive."""


class IssueFileCreateError(RobonomicsReportServiceError):
    """Failed to create issue description file."""


# for ha_storage.py
class StorageError(RobonomicsReportServiceError):
    """Failed to load/save/remove integration storage."""


# for ipfs.py
class IPFSError(RobonomicsReportServiceError):
    """IPFS/Pinata operation failed."""


class PinataKeysRevokedError(IPFSError):
    """Pinata API key has been revoked."""


# for robonomics.py
class RobonomicsError(RobonomicsReportServiceError):
    """Robonomics operation failed."""


# for report_service.py
class ReportInputError(RobonomicsReportServiceError):
    """Report cannot be created due to missing/invalid inputs."""
