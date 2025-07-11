class ChunkedUploadError(Exception):
    """Base error for chunked uploader."""

class UploadExpiredError(ChunkedUploadError):
    """Raised when an upload has expired."""

class ChecksumMismatchError(ChunkedUploadError):
    """Raised when checksum validation fails."""
