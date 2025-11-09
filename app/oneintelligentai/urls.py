from django.urls import path
from .views import chat_api, audio_chat_api, image_chat_api

urlpatterns = [
    path("chat/", chat_api, name="chat_api"),
    path("audio-chat/", audio_chat_api, name="audio_chat_api"),
    path("image-chat/", image_chat_api, name="image_chat_api"),
]
