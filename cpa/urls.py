from django.contrib import admin
from django.urls import path, include

admin.site.site_header = 'Capstone Projects Allocator - Admin'
admin.site.site_title = 'Capstone Projects Allocator - Admin'
admin.site.index_title = 'Site Administration'


urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    # path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls'), name='core'),

    path('manager/', include('manager.urls'), name='manager'),
    path('student/', include('student.urls'), name='student'),




    path('__debug__/', include('debug_toolbar.urls')),
    path('__reload__/', include('django_browser_reload.urls')),
]
