from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls'), name='core'),
    path('__debug__/', include('debug_toolbar.urls')),
]
