from django.utils.safestring import mark_safe

import django_filters
from django_filters import rest_framework as filters

from rest_framework import viewsets

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
    filterset_class = IlmFilter
    text = ''

    @action(detail=False)
    def forecasts(self, request):
        self.text = 'Ilmaennustus 48h'
        forecasts = get_forecasts()
        return Response(forecasts)

    @action(detail=False)
    def now(self, request):
        self.text = 'Hetkeilm'
        hetkeilm = get_ilmateenistus_now()
        return Response(hetkeilm)

    def get_view_name(self) -> str:
        return ' - '.join(["Ilmaandmed", self.text])

    def get_view_description(self, html=False) -> str:
        if self.text:
            text = self.text
        else:
            text = """
            Valga linna ilmaandmed:<br>
            /api/i?y=aasta<br>
            /api/i?y=aasta&m=kuu<br>
            /api/i?y=aasta&m=kuu&d=päev<br>
            /api/i?y=aasta&m=kuu&d=päev&h=tund<br>
            /api/i/now/ - Valga linna hetkeilm<br>
            /api/i/forecasts/ - Valga linna ilmaennustus kolmest allikast
            """
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text


class JaamViewSet(viewsets.ModelViewSet):
    queryset = Jaam.objects.all()
    serializer_class = JaamSerializer

    def get_view_name(self) -> str:
        return "Ilmajaamad"

    def get_view_description(self, html=False) -> str:
        text = "Valga linna ilmajaamad"
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text

