from django.contrib import admin
from django.urls import path, include

# DELETE
from preferences.load_preferences import load_prefs
load_prefs()
# DELETE


admin.site.site_header = 'Capstone Projects Allocator - Admin'
admin.site.site_title = 'Capstone Projects Allocator - Admin'
admin.site.index_title = 'Site Administration'


urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('', include('core.urls'), name='core'),

    path('manager/', include('manager.urls', namespace='manager'), name='manager'),
    path('student/', include('student.urls', namespace='student'),
         name='student'),

    path('__debug__/', include('debug_toolbar.urls')),
    path('__reload__/', include('django_browser_reload.urls')),
]
