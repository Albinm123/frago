import os
import logging
from django.dispatch import Signal
from .utils import get_chunk_model

logger = logging.getLogger(__name__)

upload_started = Signal()
chunk_received = Signal()
upload_completed = Signal()
checksum_failed = Signal()

def create_chunk_upload_dir(sender,upload,**kwargs):
    path = upload.upload_dir()
    try:
        os.makedirs(path, exist_ok = True)
        logger.info(f"Upload directory created: {path}")
    except OSError as e:
        logger.error(f"Failed to create upload directory {path}: {e}")
        
def cleanup_chunks_db(sender,upload,**kwargs):
    try:
        chunk_model=get_chunk_model()
        delete_count, _ = chunk_model.objects.filter(upload = upload).delete()
        logger.info(f'Removed {delete_count} chunk metadata for {upload.upload_id} from db ')
    except Exception as e:
        logger.error(f"Failed to remove upload db records for {upload.upload.id} : {e}")
