import os
import time
import shutil
from .conf import get_setting
from .logger import logger

class LocalFileStorageBackend:
    def save_chunk(self, upload, start, chunk_file):
        chunk_path = os.path.join(upload.upload_dir(), f"{start}.chunk")
        tmp_path = chunk_path + ".tmp"
        with open(tmp_path, 'wb') as dest:
            shutil.copyfileobj(chunk_file.file, dest, length=1024 * 1024)
        os.replace(tmp_path, chunk_path)
        logger.info(f"Saved chunk at {chunk_path}")

    def assemble_chunks(self, upload, chunks, checksum_enabled=True, algo=None):
        read_size = get_setting("ASSEMBLE_READ_SIZE")
        assembled_path = upload.assembled_path()
        assembled_dir = os.path.dirname(assembled_path)
        os.makedirs(assembled_dir, exist_ok=True)

        if checksum_enabled:
            import hashlib
            algo = algo or get_setting("CHECKSUM_TYPE")
            h = hashlib.new(algo)
            
        if os.path.exists(assembled_path):
            base, ext = os.path.splitext(assembled_path)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            new_name = f"{base}_{timestamp}{ext}"
            os.rename(assembled_path, new_name)

        with open(assembled_path, 'wb') as dest:
            for c in chunks.order_by('start'):
                with open(c.path(), 'rb') as src:
                    for block in iter(lambda: src.read(read_size), b''):
                        dest.write(block)
                        if checksum_enabled:
                            h.update(block)
                            
        logger.info(f"Assembled file at {assembled_path}")
        return h.hexdigest() if checksum_enabled else None

    def cleanup_chunks(self, upload):
        if upload.status != 'in_progress':
            chunk_dir = upload.upload_dir()
            if os.path.isdir(chunk_dir):
                try:
                    shutil.rmtree(chunk_dir)
                    logger.info(f"Successfully cleaned up chunk directory for upload ID {upload.upload_id}")
                except Exception as e:
                    logger.error(f"Failed to clean up chunk directory for upload ID {upload.upload_id}: {e}")
                    
