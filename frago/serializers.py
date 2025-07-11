from rest_framework import serializers
from .utils import get_chunk_model,get_upload_model


class ChunkedUploadChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_chunk_model()
        fields = ['start', 'end', 'size']

class ChunkedUploadSerializer(serializers.ModelSerializer):
    chunks = ChunkedUploadChunkSerializer(many=True, read_only=True)

    class Meta:
        model = get_upload_model()
        fields = ['upload_id', 'filename', 'total_size', 'status', 'created_at', 'completed_at', 'chunks']
        read_only_fields = ['status', 'created_at', 'completed_at', 'chunks']
