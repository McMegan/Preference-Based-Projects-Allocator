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
            views.UnitStudentsUploadListView.as_view(), name='unit-students-new-list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/clear$',
            views.UnitStudentsClearView.as_view(), name='unit-students-clear'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new$',
            views.UnitStudentCreateView.as_view(), name='unit-students-new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)$',
            views.UnitStudentDetailView.as_view(), name='unit-student-detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)/update$',
            views.UnitStudentUpdateView.as_view(), name='unit-student-update'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)/remove$',
            views.UnitStudentDeleteView.as_view(), name='unit-student-remove'),
    # Unit project views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects$',
            views.UnitProjectsListView.as_view(), name='unit-projects'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/new_list$',
            views.UnitProjectsUploadListView.as_view(), name='unit-projects-new-list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/clear$',
            views.UnitProjectsClearView.as_view(), name='unit-projects-clear'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/new$',
            views.UnitProjectCreateView.as_view(), name='unit-projects-new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)$',
            views.UnitProjectDetailView.as_view(), name='unit-project-detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)/update$',
            views.UnitProjectUpdateView.as_view(), name='unit-project-update'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)/remove$',
            views.UnitProjectDeleteView.as_view(), name='unit-project-remove'),
    # Unit preference views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/preferences$',
            views.UnitPreferencesView.as_view(), name='unit-preferences'),
    # Unit allocation views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/allocation$',
            views.UnitAllocationStartView.as_view(), name='unit-allocation-start'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/allocation/results$',
            views.UnitAllocationResultsView.as_view(), name='unit-allocation-results'),
]
