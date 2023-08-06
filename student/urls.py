from django.urls import path
from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='student-index'),

    path('units/<pk>/',
         views.UnitDetailView.as_view(), name='student-unit-detail'),
]
