from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from CoreFisica.media_protegida import servir_media
from django.urls import re_path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('CoreFisica.urls')),
    path('api/v1/', include('CoreFisica.urls')),
    # /media/: fotos de personas y certificados solo con la firma del enlace o con sesión (CoreFisica/media_protegida.py).
    re_path(r'^media/(?P<path>.*)$', servir_media),
]

