import django_filters
from django_filters import rest_framework as filters
from rest_framework import viewsets

from .models import Ilm, Jaam
from .serializers import IlmSerializer, JaamSerializer

class IlmFilter(filters.FilterSet):
    # Võimaldab API päringuid: http://18.196.203.237:8000/api/i/?m=2&y=2013&d=24&h=12
    # või http://18.196.203.237:8000/api/i/?y=2013
    m = django_filters.NumberFilter(field_name='timestamp', lookup_expr='month')
    y = django_filters.NumberFilter(field_name='timestamp', lookup_expr='year')
    d = django_filters.NumberFilter(field_name='timestamp', lookup_expr='day')
    h = django_filters.NumberFilter(field_name='timestamp', lookup_expr='hour')


class IlmViewSet(viewsets.ModelViewSet):
    queryset = Ilm.objects.all().order_by('-timestamp')
    serializer_class = IlmSerializer
    # Järgnev vajalik, et saaks teha filtreeritud API päringuid
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = IlmFilter


class JaamViewSet(viewsets.ModelViewSet):
    queryset = Jaam.objects.all()
    serializer_class = JaamSerializer
    
    