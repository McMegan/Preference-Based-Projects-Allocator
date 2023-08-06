from django.urls import path
from . import views
from . import forms

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('units/new', views.UnitCreateView.as_view(), name='unit-new'),
    path('units/<pk>/',
         views.UnitDetailView.as_view(), name='unit-detail'),
    path('units/<pk>/delete',
         views.UnitDeleteView.as_view(), name='unit-delete'),
    path('units/<pk>/edit',
         views.UnitUpdateView.as_view(), name='unit-edit'),
]
