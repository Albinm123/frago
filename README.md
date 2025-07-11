# Frago

**Frago** is a reusable Django app that provides a secure, resumable, and parallel chunked file upload system. It supports large file uploads with resumable support, duplicate chunk detection, checksum verification, and customizable signal hooks — ideal for drone videos, media applications, and IoT devices.

---

## 🚀 Features

- Parallel & resumable chunked uploads
- Upload tracking via database (start, end, size per chunk)
- Checksum verification (MD5 or other algorithms)
- Duplicate chunk detection
- Upload expiration support
- Extensible via Django signals
- Pluggable authentication (user/device/anonymous)
- Local file storage (pluggable)

---

## 📦 Installation

```bash
pip install frago

Add frago to your Django INSTALLED_APPS:
    # settings.py
    INSTALLED_APPS = [
        ...
        "frago",
    ]

Finally, run the following commands to create and apply the migrations:

    python manage.py makemigrations frago
    
    python manage.py migrate
    
```
## ⚙️ Configuration (optional) 
```bash
you can confic these in settings.py

#🧠 How the uploader identifies the upload session

CHUNKED_UPLOADER_IDENTIFIER_MODE = "user"
 Options: "anonymous" (default), "user"
 You can override get_identifier() for custom logic.

# 📂 Where uploaded chunks are stored temporarily
CHUNKED_UPLOADER_CHUNK_UPLOAD_PATH = "chunked_uploads/"

# 📂 Where final assembled files go
CHUNKED_UPLOADER_ASSEMBLED_PATH = "assembled_videos/"

# 🔐 Hash type for file integrity checks
CHUNKED_UPLOADER_CHECKSUM_TYPE = "md5"
 Any hashlib-supported algorithm (e.g., "sha256")

# ✅ Whether to perform checksum verification
CHUNKED_UPLOADER_DO_CHECKSUM = True

# ⏱️ Chunk expiration time (used for cleanup jobs)
CHUNKED_UPLOADER_EXPIRATION = timedelta(days=1)

# 📦 Read buffer size during assembly
CHUNKED_UPLOADER_ASSEMBLE_READ_SIZE = 8 * 1024 * 1024  # 8MB

# 🧱 Custom chunk model path (if overriding)
CHUNKED_UPLOADER_CHUNK_MODEL = "frago.ChunkedUploadChunk"

# 🧩 Custom upload model path (if overriding)
CHUNKED_UPLOADER_UPLOAD_MODEL = "frago.ChunkUpload"
```

## 🧩 API Usage
    1. Start a new upload

```bash
        POST /upload/
        Request:
        {
        "filename": "video.mp4",
        "total_size": 104857600
        }

        Response:
        {
        "status": true,
        "upload_id": "uuid4-string",
        "message": "Upload started for video.mp4"
        }
```
    2. Upload a chunk

```bash
        PUT /upload/{upload_id}/

        Headers:
            Content-Range: bytes 0-1048575/104857600

        Body: multipart/form-data with key file and binary chunk data.
```    
    3. Finalize upload

```bash
        POST /upload/{upload_id}/

        Request
        {
        "checksum": "d41d8cd98f00b204e9800998ecf8427e",
        "checksum_algo": "md5"
        }

        Response
        {
        "status": true,
        "upload_id": "uuid4-string",
        "message": "Upload completed for video.mp4"
        }
```
    4. Get upload status (only for authenticated users)

```bash
        GET /upload/{upload_id}/

        Or list uploads by current user/device:
        GET /upload/
```

## 🧠 Models
    ChunkUpload

        Tracks a single upload:

            upload_id: UUID

            filename, total_size

            status: in_progress, complete, expired

            created_at, completed_at

    ChunkedUploadChunk

        Tracks individual uploaded chunks:

            start, end, size

            Foreign key to ChunkUpload

## 🧰 Signals

    Frago emits the following Django signals:
    Signal	Triggered When
        upload_started : New upload is created
        chunk_received	: A chunk is received and saved
        upload_completed : All chunks assembled, upload finalized
        checksum_failed : Checksum mismatch during finalization

    To extend behavior, connect signal handlers:

```bash
        from frago.signals import upload_started
        def my_handler(sender, upload, **kwargs):
            print("Upload started:", upload.filename)

        upload_started.connect(my_handler)
```

## 🧪 Usage Example
    Add to your urls.py (if you are using with out any overides):
```bash

        path('api/',include('frago.urls')),
```

## 🧼 Cleanup:
    Uploads expire after a period (EXPIRATION) and are marked expired.
    Chunks and their metadata are deleted automatically on completion.


# OVERIDING

This is an example how you can overide and set your custome logic

## 🔒 Custom Authentication Example

By default, the view allows anonymous access. You should subclass the view and add authentication:

```bash
    from rest_framework.permissions import IsAuthenticated
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from frago.views import ParallelChunkedUploadView

    class SecureUploadView(ParallelChunkedUploadView):
        authentication_classes = [JWTAuthentication]
        permission_classes = [IsAuthenticated]
```

## 🧠 Overriding the Identifier
```bash
    class MyView(ParallelChunkedUploadView):
        authentication_classes = [CustomAuthentication]
        
        identifier_field = 'device'

        def get_identifier(self, request):
            if self.IDENTIFIER_MODE == 'device':
                
                device_id = request.user

                if not device_id:
                    raise PermissionDenied("Device ID not found.")

                try:
                    device = Devices.objects.get(inventory_id=device_id)
                    print('device',device.id)
                    return device  # or another unique identifier
                except Devices.DoesNotExist:
                    raise PermissionDenied("Invalid Device ID.")

            # fallback to parent logic
            return super().get_identifier(request)
        
```
Update your urls.py:

```bash
    urlpatterns = [
        path('upload/',MyView.as_view()),
        path('upload/<uuid:pk>/', MyView.as_view()),
    ]
```

## 🔧 Custom Upload Model Example
```bash
    class Mychunkupload(AbstractChunkUpload):
        device = models.ForeignKey(Devices,on_delete=models.CASCADE)
        

        def assembled_path(self):
            try:
                device = Devices.objects.get(inventory_id=self.device_id)
                base_path = device.videos or settings.ASSEMBLED_PATH
            except Exception as e:
                base_path = settings.ASSEMBLED_PATH
            return os.path.join(base_path, f'{self.filename}')
        
```
Register it in settings:

```bash
    CHUNKED_UPLOADER_UPLOAD_MODEL = 'fragotest.Mychunkupload'
```

and specify the identifier field in the view 

```bash
    identifier_field = 'device'
```



## 🔗 Uploader Client

Use the official uploader client:  
👉 [frago-client](https://github.com/Albinm123/frago-client.git)



## 📄 License
    This project is licensed under the MIT License.


## 🤝 Contributing
    Pull requests are welcome! 
    Please open an issue first to discuss your idea.
    Make sure to add tests for any new features or logic changes.

## 🙌 Author
    Built with ❤️ to support scalable file upload workflows in Django.
    Let me know if you want:
        Markdown preview badges
        GitHub Actions/test coverage
        Python client script (httpx/requests)