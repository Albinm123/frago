from django.apps import apps
from .conf import get_setting

def get_upload_model():
    model_path = get_setting('UPLOAD_MODEL')
    return apps.get_model(model_path)

def get_chunk_model():
    model_path = get_setting('CHUNK_MODEL')
    return apps.get_model(model_path)
