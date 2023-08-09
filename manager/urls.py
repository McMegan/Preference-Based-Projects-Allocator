from django.urls import path, re_path
from . import views
from . import forms

urlpatterns = [
    path('', views.IndexView.as_view(), name='manager-index'),
    # Unit views
    path('units/new', views.UnitCreateView.as_view(), name='manager-unit-new'),
    path('units/<pk>/',
         views.UnitDetailView.as_view(), name='manager-unit-detail'),
    path('units/<pk>/delete',
         views.UnitDeleteView.as_view(), name='manager-unit-delete'),
    # Unit student views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students$',
            views.UnitStudentsListView.as_view(), name='manager-unit-students'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new$',
            views.UnitStudentsCreateView.as_view(), name='manager-unit-students-new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new_list$',
            views.UnitStudentUploadListView.as_view(), name='manager-unit-students-new-list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)$',
            views.UnitStudentsDetailView.as_view(), name='manager-unit-students-detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)/remove$',
            views.UnitStudentsDeleteView.as_view(), name='unit-students-remove'),
]
