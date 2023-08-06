from django.urls import path, re_path
from . import views
from . import forms

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    # Unit views
    path('units/new', views.UnitCreateView.as_view(), name='unit-new'),
    path('units/<pk>/',
         views.UnitDetailView.as_view(), name='unit-detail'),
    path('units/<pk>/delete',
         views.UnitDeleteView.as_view(), name='unit-delete'),
    path('units/<pk>/edit',
         views.UnitUpdateView.as_view(), name='unit-edit'),
    # Unit student views
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students$',
            views.UnitStudentsListView.as_view(), name='unit-students'),
    re_path(r'^units/(?P<pk_unit>[0-9]+)/students/new$',
            views.UnitStudentsListView.as_view(), name='unit-students-new'),
    # re_path(r'^units/(?P<pk_unit>[0-9]+)/students/(?P<pk_student>[0-9]+)/remove$',views.UnitStudentsListView.as_view(), name='unit-students-remove'),
]
