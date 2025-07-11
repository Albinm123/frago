from django.conf import settings
from datetime import timedelta

DEFAULTS = {
    'IDENTIFIER_MODE': 'user',
    'CHUNK_UPLOAD_PATH': 'chunked_uploads/',
    'ASSEMBLED_PATH': 'assembled_videos/',
    'CHECKSUM_TYPE': 'md5',
    'DO_CHECKSUM': True,
    'EXPIRATION': timedelta(days=1),
    'ASSEMBLE_READ_SIZE': 8 * 1024 * 1024,  # 8 MB
    'IDENTIFIER_MODE':'anonymous',
    'CHUNK_MODEL': 'frago.ChunkedUploadChunk',
    'UPLOAD_MODEL': 'frago.ChunkUpload',
}

def get_setting(name):
    return getattr(settings, f'CHUNKED_UPLOADER_{name}', DEFAULTS[name])
