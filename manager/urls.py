from django.urls import path, re_path

from . import views

app_name = 'manager'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    # Unit views
    path('units/new/', views.UnitCreateView.as_view(), name='unit_create'),
    path('units/<pk>/',
         views.UnitDetailView.as_view(), name='unit'),
    path('units/<pk>/update/',
         views.UnitUpdateView.as_view(), name='unit_update'),
    path('units/<pk>/delete/',
         views.UnitDeleteView.as_view(), name='unit_delete'),
    # Student views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/$',
            views.StudentsListView.as_view(), name='unit_students'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new_list/$',
            views.StudentsUploadListView.as_view(), name='unit_students_new_list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/clear/$',
            views.StudentsClearView.as_view(), name='unit_students_delete_all'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new/$',
            views.StudentCreateView.as_view(), name='unit_students_new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)/$',
            views.StudentDetailView.as_view(), name='unit_student_detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)/update/$',
            views.StudentUpdateView.as_view(), name='unit_student_update'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk>[0-9]+)/remove/$',
            views.StudentDeleteView.as_view(), name='unit_student_delete'),
    # Project views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/$',
            views.ProjectsListView.as_view(), name='unit_projects'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/new_list/$',
            views.ProjectsUploadListView.as_view(), name='unit_projects_new_list'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/clear/$',
            views.ProjectsClearView.as_view(), name='unit_projects_delete_all'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/new/$',
            views.ProjectCreateView.as_view(), name='unit_projects_new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)/$',
            views.ProjectDetailView.as_view(), name='unit_project_detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)/update/$',
            views.ProjectUpdateView.as_view(), name='unit_project_update'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/projects/(?P<pk>[0-9]+)/remove/$',
            views.ProjectDeleteView.as_view(), name='unit_project_delete'),
    # Area views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/$',
            views.AreasListView.as_view(), name='unit_areas'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/clear/$',
            views.AreasClearView.as_view(), name='unit_areas_delete_all'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/new/$',
            views.AreaCreateView.as_view(), name='unit_areas_new'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/(?P<pk>[0-9]+)/$',
            views.AreaDetailView.as_view(), name='unit_area_detail'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/(?P<pk>[0-9]+)/update/$',
            views.AreaUpdateView.as_view(), name='unit_area_update'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/areas/(?P<pk>[0-9]+)/remove/$',
            views.AreaDeleteView.as_view(), name='unit_area_delete'),
    # Preference views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/preferences/$',
            views.PreferencesView.as_view(), name='unit_preferences'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/preferences/distribution/$',
            views.PreferencesDistributionView.as_view(), name='unit_preferences_distribution'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/preferences/upload/$',
            views.PreferencesUploadListView.as_view(), name='unit_preferences_new_list'),
    # Allocation Views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/allocation/$',
            views.AllocationView.as_view(), name='unit_allocation')
]
