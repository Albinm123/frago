import re
from django.db import transaction
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.generics import GenericAPIView
from .serializers import ChunkedUploadSerializer
from .conf import get_setting
from django.core.exceptions import PermissionDenied
from .storage import LocalFileStorageBackend
from .signals import upload_started, chunk_received, upload_completed, checksum_failed
from .logger import logger
from rest_framework import status
from .utils import get_upload_model,get_chunk_model


class ParallelChunkedUploadView(GenericAPIView):
    """
        A generic view for handling parallel, resumable chunked uploads.

        Supported operations:
        - POST (no `pk`): Initiate a new upload session.
        - POST (with `pk`): Finalize an upload by assembling chunks and verifying checksum.
        - PUT (with `pk`): Upload individual file chunks.
        - GET (with or without `pk`): Retrieve upload status or list of uploads.

        Notes:
            - Requires Content-Range header for chunk uploads.
            - Duplicate chunks are ignored if already uploaded.
            - Assembles and optionally validates final file via checksum.
            
        You should set authentication_classes and permission_classes
        in your project, or subclass this view.
    """
    IDENTIFIER_MODE = get_setting('IDENTIFIER_MODE')

    
    authentication_classes = []
    permission_classes = []
    serializer_class = ChunkedUploadSerializer
    storage = LocalFileStorageBackend()
    field_name = 'file'
    identifier_field = 'identifier'
    content_range_re = re.compile(r'^bytes (?P<start>\d+)-(?P<end>\d+)/(?P<total>\d+)$')
    
    @property
    def upload_model(self):
        """Returns the upload model (customizable via settings)."""
        return get_upload_model()

    @property
    def chunk_model(self):
        """Returns the chunk model (customizable via settings)."""
        return get_chunk_model()
    
    def get_queryset(self):
        return self.upload_model.objects.all()

    def get_identifier(self, request):
        """
        Resolves an identifier for associating uploads.

        Supports modes:
            - 'device': uses request.user (e.g., for device-linked auth)
            - 'user': uses authenticated user ID
            - 'anonymous': returns None
        
        """
        if self.IDENTIFIER_MODE == 'user':
            if request.user and request.user.is_authenticated:
                return request.user
            else:
                raise PermissionDenied("User not authenticated.")


        if self.IDENTIFIER_MODE == 'anonymous':
            return None

        else:
            raise ValueError("Invalid CHUNKED_UPLOADER_IDENTIFIER_MODE")

    def put(self, request, pk=None):
        """
        Handles chunk uploads.

        Requires:
            - `Content-Range` header specifying start, end, total bytes.
            - File data in `file` field.
        """
        upload = get_object_or_404(self.get_queryset(), upload_id=pk)
        
        # Check if upload has expired
        if upload.status == upload.STATUS_EXPIRED or upload.is_expired():
            upload.mark_expired()
            self.storage.cleanup_chunks(upload)
            upload_completed.send(sender=self.__class__,upload=upload)
            return Response({'status': False,'error': 'Upload expired'}, status=status.HTTP_410_GONE)

        content_range = request.META.get('HTTP_CONTENT_RANGE')
        if not content_range:
            return Response({'status': False,'error': 'Missing Content-Range header'}, status=status.HTTP_400_BAD_REQUEST)

        match = self.content_range_re.match(content_range)
        if not match:
            return Response({'status': False,'error': 'Invalid Content-Range header'}, status=status.HTTP_400_BAD_REQUEST)

        # Extract start, end, and total size from header
        start, end, total = map(int, (match.group('start'), match.group('end'), match.group('total')))

        if total != upload.total_size:
            return Response({'status': False,'error': 'Total size mismatch'}, status=status.HTTP_400_BAD_REQUEST)

        chunk_file = request.data.get(self.field_name)
        if not chunk_file:
            return Response({'status': False,'error': 'No chunk provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        expected_size = end - start + 1
        if chunk_file.size != expected_size:
            return Response({'status': False, 'error': f'Chunk size mismatch (expected {expected_size}, got {chunk_file.size})'}, status=status.HTTP_400_BAD_REQUEST)      
        
        # Avoid duplicate chunk writes 
        existing_chunk = self.chunk_model.objects.filter(upload=upload, start=start).first()
        if existing_chunk and existing_chunk.size == chunk_file.size:
            logger.info(f"Duplicate chunk detected for start={start}; skipping save.")
            return Response(
                {
                    'status': True,
                    'message': 'Duplicate chunk already uploaded; skipped',
                    'start': start,
                    'end': end,
                    'size': chunk_file.size,
                    'duplicate': True
                },
                status=status.HTTP_200_OK
            )
  
        try:
            # Save the chunk file to storage backend
            self.storage.save_chunk(upload,start,chunk_file)
            
            # Record or update the chunk metadata
            with transaction.atomic():
                self.chunk_model.objects.update_or_create(
                    upload=upload,
                    start=start,
                    defaults={'end': end, 'size': chunk_file.size}
                )
            # Emit signal
            chunk_received.send(sender=self.__class__,upload=upload,start=start)
            return Response({'status': True,'message': 'Chunk uploaded', 'start': start, 'end': end, 'size': chunk_file.size}, status=200)
        except Exception as e:
            logger.exception("Unhandled error during chunk upload for upload_id=%s, start=%s", pk, start)
            return Response({'status': False, 'error': f'Chunk upload failed: {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def post(self, request, pk=None):
        """
        Handles two use-cases:
        - Initiate a new upload (no `pk`)
        - Finalize an upload and assemble the file (with `pk`)
        """
        # =================================== Step 1: Start a new upload =============================================

        if not pk:
            filename = request.data.get('filename') or None
            total_size = request.data.get('total_size') or None

            if not filename or not total_size:
                return Response({'status': False,'message': 'filename and total_size required'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                identifier = self.get_identifier(request)
                extra_kwargs = {
                self.identifier_field: identifier
                }
                with transaction.atomic():
                    upload = self.upload_model.objects.create(
                        filename=filename,
                        total_size=int(total_size),
                        **extra_kwargs
                    )
                upload_started.send(sender=self.__class__, upload = upload)
                logger.info(f'Upload started for {upload.upload_id}')
                return Response({'status': True,'message':f"Upload started for {upload.filename}", 'upload_id': str(upload.upload_id)}, status=201)
            except Exception as e:
                logger.exception('Unhandled error during new upload creation file name=%s,size=%s,identifier=%s',filename,total_size,identifier)
                return Response({'status': False,'message': f'Upload faild {str(e)}'}, status=500)     
             
    # ======================= Step 2: Finalize an existing upload ====================================================

        upload = get_object_or_404(self.get_queryset(), upload_id=pk)
        
        if not upload.all_chunks_received():
            return Response({'status': False,'message': 'Not all chunks uploaded'}, status=status.HTTP_400_BAD_REQUEST)
        
        checksum_enabled=get_setting("DO_CHECKSUM")
        client_checksum = None
        algo = 'md5'
        
        if checksum_enabled:
            client_checksum = request.data.get('checksum')
            algo = request.data.get('checksum_algo', 'md5')
            
            if not client_checksum:
                return Response({'status': False,'message': 'Checksum required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Assemble chunks and validate checksum if enabled
            server_checksum = self.storage.assemble_chunks(upload,upload.chunks.all() ,checksum_enabled, algo=algo)
            if server_checksum and server_checksum != client_checksum:
                checksum_failed.send(sender=self.__class__, upload = upload)
                return Response({'status': False, 'message': 'Checksum mismatch'}, status=status.HTTP_400_BAD_REQUEST)

            # Finalize upload
            upload.mark_complete()
            self.storage.cleanup_chunks(upload)
            upload_completed.send(sender=self.__class__,upload=upload)
                    
            return Response({'status': True, 'message':f'Upload completed for {upload.filename}','upload_id': str(upload.upload_id)}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception('Unhandled error during upload completion id=%s',upload.upload_id)
            return Response({'status': False, 'message': f'Finalization failed: {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def get(self, request, pk=None):
        """
        Returns upload info.

        - If `pk` is provided: returns info for specific upload.
        - If no `pk`: returns all uploads for the identifier (user/device/anonymous).
        """
        identifier = self.get_identifier(request)
        if identifier != "anonymous": 
            if pk:
                upload = get_object_or_404(self.get_queryset(), upload_id=pk)
                return Response(self.get_serializer(upload, context={'request': request}).data)
            else: 
                uploads = self.get_queryset().filter(**{self.identifier_field: identifier})
                return Response(self.get_serializer(uploads, many=True, context={'request': request}).data)
        return Response({'status': False, 'message': f'anonymous users can not view uploads '},status=status.HTTP_403_FORBIDDEN)
 