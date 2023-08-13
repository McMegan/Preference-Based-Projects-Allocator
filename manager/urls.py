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
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new_list$',
            views.UnitStudentUploadListView.as_view(), name='manager-unit-students-new-list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/clear$',
            views.UnitStudentsClearView.as_view(), name='manager-unit-students-clear'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new$',
            views.UnitStudentsCreateView.as_view(), name='manager-unit-students-new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)$',
            views.UnitStudentsDetailView.as_view(), name='manager-unit-students-detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)/remove$',
            views.UnitStudentDeleteView.as_view(), name='manager-unit-student-remove'),
    # Unit project views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/project$',
            views.UnitProjectsListView.as_view(), name='manager-unit-projects'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/new_list$',
            views.UnitProjectUploadListView.as_view(), name='manager-unit-projects-new-list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/clear$',
            views.UnitProjectsClearView.as_view(), name='manager-unit-projects-clear'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/new$',
            views.UnitProjectsCreateView.as_view(), name='manager-unit-projects-new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)$',
            views.UnitProjectsUpdateView.as_view(), name='manager-unit-projects-edit'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)/remove$',
            views.UnitProjectDeleteView.as_view(), name='manager-unit-project-remove'),
    # Unit preference views
    # Unit allocation views
]
