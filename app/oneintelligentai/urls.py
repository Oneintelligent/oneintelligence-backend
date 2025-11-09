from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat_api, name='chat'),
    path('audio-chat/', views.audio_chat_api, name='audio-chat'),
    path('image-chat/', views.image_chat_api, name='image-chat'),
]
