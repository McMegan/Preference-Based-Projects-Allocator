import django_filters
from core import models


class ProjectFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='contains', label='Name')

    class Meta:
        model = models.Project
        fields = ['name']
