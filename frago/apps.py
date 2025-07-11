from django.apps import AppConfig

class FragoConfig(AppConfig):
    name = "frago"
    def ready(self):
        from .signals import create_chunk_upload_dir,cleanup_chunks_db,upload_started,upload_completed
        upload_started.connect(create_chunk_upload_dir)
        upload_completed.connect(cleanup_chunks_db)
        
        super().ready()