import os

from django.contrib import admin
from django.urls import path, include

from .healthcheck import HealthCheckView

admin.site.site_header = 'Capstone Projects Allocator - Admin'
admin.site.site_title = 'Capstone Projects Allocator - Admin'
admin.site.index_title = 'Site Administration'


urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('', include('core.urls'), name='core'),

    path('manager/', include('manager.urls', namespace='manager'), name='manager'),
    path('student/', include('student.urls', namespace='student'),
         name='student'),

    path('health/', HealthCheckView.as_view(), name='health_check_home'),
]


if 'WEBSITE_HOSTNAME' not in os.environ:
    urlpatterns = urlpatterns + [
        path('__debug__/', include('debug_toolbar.urls')),
        path('__reload__/', include('django_browser_reload.urls')),
    ]
