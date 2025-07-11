from django.urls import path
from .views import ParallelChunkedUploadView

urlpatterns = [
    path('upload/',ParallelChunkedUploadView.as_view()),
    path('upload/<uuid:pk>/', ParallelChunkedUploadView.as_view()),
]