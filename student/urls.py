from django.urls import path
from . import views


app_name = 'student'


urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('units/<pk>/',
         views.UnitDetailView.as_view(), name='unit-detail'),
]
