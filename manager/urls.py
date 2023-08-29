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
    # Student views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students$',
            views.StudentsListView.as_view(), name='unit-students'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new_list$',
            views.StudentsUploadListView.as_view(), name='unit-students-new-list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/clear$',
            views.StudentsClearView.as_view(), name='unit-students-clear'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new$',
            views.StudentCreateView.as_view(), name='unit-students-new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)$',
            views.StudentDetailView.as_view(), name='unit-student-detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)/update$',
            views.StudentUpdateView.as_view(), name='unit-student-update'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)/remove$',
            views.StudentDeleteView.as_view(), name='unit-student-remove'),
    # Project views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects$',
            views.ProjectsListView.as_view(), name='unit-projects'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/new_list$',
            views.ProjectsUploadListView.as_view(), name='unit-projects-new-list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/clear$',
            views.ProjectsClearView.as_view(), name='unit-projects-clear'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/new$',
            views.ProjectCreateView.as_view(), name='unit-projects-new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)$',
            views.ProjectDetailView.as_view(), name='unit-project-detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)/update$',
            views.ProjectUpdateView.as_view(), name='unit-project-update'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)/remove$',
            views.ProjectDeleteView.as_view(), name='unit-project-remove'),
    # Area views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas$',
            views.AreasListView.as_view(), name='unit-areas'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/clear$',
            views.AreasClearView.as_view(), name='unit-areas-clear'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/new$',
            views.AreaCreateView.as_view(), name='unit-area-new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/(?P<pk>[0-9]+)$',
            views.AreaDetailView.as_view(), name='unit-area-detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/(?P<pk>[0-9]+)/update$',
            views.AreaUpdateView.as_view(), name='unit-area-update'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/(?P<pk>[0-9]+)/remove$',
            views.AreaDeleteView.as_view(), name='unit-area-remove'),
    # Preference views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/preferences$',
            views.PreferencesView.as_view(), name='unit-preferences'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/preferences-distribution$',
            views.PreferencesDistributionView.as_view(), name='unit-preferences-distribution'),
    # Allocation Views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/allocation$',
            views.AllocationStartView.as_view(), name='unit-allocation-start'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/allocation/results$',
            views.AllocationResultsView.as_view(), name='unit-allocation-results'),
]
