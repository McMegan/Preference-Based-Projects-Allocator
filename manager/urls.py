from django.urls import path, re_path
from . import views

app_name = 'manager'


urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    # Unit views
    path('units/new/', views.UnitCreateView.as_view(), name='unit-new'),
    path('units/<pk>/',
         views.UnitView.as_view(), name='unit'),
    path('units/<pk>/delete',
         views.UnitDeleteView.as_view(), name='unit-delete'),
    # Unit student views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students$',
            views.UnitStudentsListView.as_view(), name='unit-students'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new_list$',
            views.UnitStudentUploadListView.as_view(), name='unit-students-new-list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/clear$',
            views.UnitStudentsClearView.as_view(), name='unit-students-clear'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new$',
            views.UnitStudentsCreateView.as_view(), name='unit-students-new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)$',
            views.UnitStudentsDetailView.as_view(), name='unit-students-detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)/remove$',
            views.UnitStudentDeleteView.as_view(), name='unit-student-remove'),
    # Unit project views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects$',
            views.UnitProjectsListView.as_view(), name='unit-projects'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/new_list$',
            views.UnitProjectUploadListView.as_view(), name='unit-projects-new-list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/clear$',
            views.UnitProjectsClearView.as_view(), name='unit-projects-clear'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/new$',
            views.UnitProjectsCreateView.as_view(), name='unit-projects-new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)$',
            views.UnitProjectsUpdateView.as_view(), name='unit-projects-edit'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)/remove$',
            views.UnitProjectDeleteView.as_view(), name='unit-project-remove'),
    # Unit preference views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/preferences$',
            views.UnitPreferencesListView.as_view(), name='unit-preferences'),
    # Unit allocation views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/allocation/start$',
            views.UnitAllocationStartView.as_view(), name='unit-allocation-start'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/allocation/$',
            views.UnitAllocationListView.as_view(), name='unit-allocation'),
]
