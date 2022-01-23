import django_filters
from django_filters import rest_framework as filters
from rest_framework import viewsets, generics

from .models import Ilm, Jaam
from .serializers import IlmSerializer, JaamSerializer
from .views import get_forecasts, get_ilmateenistus_now

class IlmFilter(filters.FilterSet):
    # Võimaldab API päringuid: http://18.196.203.237:8000/api/i/?m=2&y=2013&d=24&h=12
    # või http://18.196.203.237:8000/api/i/?y=2013
    m = django_filters.NumberFilter(field_name='timestamp', lookup_expr='month')
    y = django_filters.NumberFilter(field_name='timestamp', lookup_expr='year')
    d = django_filters.NumberFilter(field_name='timestamp', lookup_expr='day')
    h = django_filters.NumberFilter(field_name='timestamp', lookup_expr='hour')


from rest_framework.decorators import action
from rest_framework.response import Response


class IlmViewSet(viewsets.ModelViewSet):
    queryset = Ilm.objects.all().order_by('-timestamp')
    serializer_class = IlmSerializer
    # Järgnev vajalik, et saaks teha filtreeritud API päringuid
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = IlmFilter

    @action(detail=False)
    def forecasts(self, request, pk=None):
        forecasts = get_forecasts()
        return Response(forecasts)

    @action(detail=False)
    def now(self, request, pk=None):
        hetkeilm = get_ilmateenistus_now()
        return Response(hetkeilm)


class JaamViewSet(viewsets.ModelViewSet):
    queryset = Jaam.objects.all()
    serializer_class = JaamSerializer

class ForecastsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset that provides the standard actions
    """
    queryset = Ilm.objects.all()
    serializer_class = IlmSerializer
    lookup_field = 'pk'

    @action(detail=True)
    def group_names(self, request, pk=None):
        """
        Returns a list of all the group names that the given
        user belongs to.
        """
        # user = self.get_object()
        # groups = user.groups.all()
        groups = [1,2,3]
        return Response(groups)