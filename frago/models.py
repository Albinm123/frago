import os
import uuid
from .conf import get_setting
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings




class AbstractChunkUpload(models.Model):
    '''Inherit from this model if you are implementing your own.'''
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETE = 'complete'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETE, 'Complete'),
        (STATUS_EXPIRED,'Expired'),
    ]
    
    upload_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    offset = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_size = models.BigIntegerField()
    
    class Meta:
        abstract = True
        ordering = ["-completed_at"]
        
    def upload_dir(self):
        return os.path.join(get_setting("CHUNK_UPLOAD_PATH"), str(self.upload_id))

    def assembled_path(self):
        return os.path.join(get_setting("ASSEMBLED_PATH"), self.filename)

    def is_expired(self):
        if self.status == self.STATUS_IN_PROGRESS and timezone.now() >= self.created_at + get_setting("EXPIRATION"):
            return True
        return False
    
    @transaction.atomic
    def mark_expired(self):
        self.status = self.STATUS_EXPIRED
        self.save()

    @property
    def expires_at(self):
        return self.created_at + get_setting('EXPIRATION')
    
    @transaction.atomic
    def mark_complete(self):
        self.status = self.STATUS_COMPLETE
        self.completed_at = timezone.now()
        self.save()

    def all_chunks_received(self):
        chunk_size_sum = self.chunks.aggregate(total=models.Sum('size'))['total'] or 0
        return chunk_size_sum == self.total_size
      
        
class ChunkUpload(AbstractChunkUpload):
    identifier = models.CharField(max_length=200,null=True,blank=True, help_text="User ID, device ID, or other identifier")


class ChunkedUploadChunk(models.Model):
    upload = models.ForeignKey(
            to=getattr(settings, 'CHUNKED_UPLOADER_UPLOAD_MODEL', 'frago.ChunkUpload'),
            related_name='chunks',
            on_delete=models.CASCADE
        )    
    start = models.BigIntegerField()
    end = models.BigIntegerField()
    size = models.BigIntegerField()

    class Meta:
        abstract = False
        unique_together = [('upload', 'start')]
        indexes = [
            models.Index(fields=['upload', 'start']),
        ]
    def path(self):
        return os.path.join(self.upload.upload_dir(), f'{self.start}.chunk')

