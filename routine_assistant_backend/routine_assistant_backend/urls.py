"""
URL configuration for routine_assistant_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework import routers
from activities import views
from voice.views import VoiceAudioDownloadView, VoiceSTTView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('activities.urls')),
    path('api/v1/', include('users.urls')),
    path('api/v1/', include('routines.urls')),
    path('api/voice/', include('voice.urls')),
    path('assistant/stt/', VoiceSTTView.as_view(), name='assistant-stt'),
    path(
        'assistant/audio/<str:file_name>/',
        VoiceAudioDownloadView.as_view(),
        name='assistant-audio-download',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
