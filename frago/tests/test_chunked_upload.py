import io
import uuid
from django.urls import reverse
from django.test import TestCase
from django.utils import timezone
from django.conf import settings

from frago.models import ChunkUpload, ChunkedUploadChunk
from frago.signals import upload_started, upload_completed

class ChunkedUploadTestCase(TestCase):
    def setUp(self):
        self.filename = "testfile.txt"
        self.total_size = 20  # bytes
        self.chunk1 = b"Hello "
        self.chunk2 = b"World!"
        self.full_file = self.chunk1 + self.chunk2  # 13 bytes

        self.start_url = reverse("chunked-upload")  # Adjust your URLConf
        self.headers = {
            "Content-Range": "bytes 0-5/13"
        }

    def test_chunked_upload_flow(self):
        # Step 1: Start upload
        res = self.client.post(self.start_url, data={
            "filename": self.filename,
            "total_size": len(self.full_file)
        })
        self.assertEqual(res.status_code, 201)
        upload_id = res.json()['upload_id']

        # Step 2: Upload first chunk
        res = self.client.put(
            f"{self.start_url}{upload_id}/",
            data={"file": io.BytesIO(self.chunk1)},
            content_type="multipart/form-data",
            **{"HTTP_CONTENT_RANGE": f"bytes 0-5/{len(self.full_file)}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ChunkedUploadChunk.objects.count(), 1)

        # Step 3: Upload second chunk
        res = self.client.put(
            f"{self.start_url}{upload_id}/",
            data={"file": io.BytesIO(self.chunk2)},
            content_type="multipart/form-data",
            **{"HTTP_CONTENT_RANGE": f"bytes 6-12/{len(self.full_file)}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ChunkedUploadChunk.objects.count(), 2)

        # Step 4: Finalize upload
        res = self.client.post(f"{self.start_url}{upload_id}/")
        self.assertEqual(res.status_code, 201)

        upload = ChunkUpload.objects.get(upload_id=upload_id)
        self.assertEqual(upload.status, upload.STATUS_COMPLETE)

    def test_duplicate_chunk_skipped(self):
        res = self.client.post(self.start_url, data={
            "filename": self.filename,
            "total_size": len(self.full_file)
        })
        upload_id = res.json()['upload_id']

        # Upload first chunk twice
        for _ in range(2):
            res = self.client.put(
                f"{self.start_url}{upload_id}/",
                data={"file": io.BytesIO(self.chunk1)},
                content_type="multipart/form-data",
                **{"HTTP_CONTENT_RANGE": f"bytes 0-5/{len(self.full_file)}"}
            )
        self.assertIn("duplicate", res.json())

    def test_checksum_mismatch(self):
        # Enable checksum check in settings
        settings.CHUNKED_UPLOAD_CHECKSUM = True

        res = self.client.post(self.start_url, data={
            "filename": self.filename,
            "total_size": len(self.chunk1)
        })
        upload_id = res.json()['upload_id']

        self.client.put(
            f"{self.start_url}{upload_id}/",
            data={"file": io.BytesIO(self.chunk1)},
            content_type="multipart/form-data",
            **{"HTTP_CONTENT_RANGE": f"bytes 0-5/{len(self.chunk1)}"}
        )

        # Submit incorrect checksum
        res = self.client.post(f"{self.start_url}{upload_id}/", data={
            "checksum": "WRONG",
            "checksum_algo": "md5"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Checksum mismatch", res.json()["message"])

    def test_expired_upload(self):
        res = self.client.post(self.start_url, data={
            "filename": self.filename,
            "total_size": len(self.full_file)
        })
        upload_id = res.json()['upload_id']
        upload = ChunkUpload.objects.get(upload_id=upload_id)

        # Force expiration
        upload.created_at = timezone.now() - settings.CHUNK_UPLOAD_EXPIRATION - timezone.timedelta(minutes=1)
        upload.save()

        # Try to put a chunk after expiration
        res = self.client.put(
            f"{self.start_url}{upload_id}/",
            data={"file": io.BytesIO(self.chunk1)},
            content_type="multipart/form-data",
            **{"HTTP_CONTENT_RANGE": f"bytes 0-5/{len(self.full_file)}"}
        )
        self.assertEqual(res.status_code, 410)
