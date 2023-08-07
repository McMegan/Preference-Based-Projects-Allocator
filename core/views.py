from django.db import models
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect
from django.db.models import Count

from . import models
from . import forms


def index_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_student:
        return redirect('student-index')
    if request.user.is_manager:
        return redirect('manager-index')
    if request.user.is_superuser:
        return redirect('admin')
    return None
