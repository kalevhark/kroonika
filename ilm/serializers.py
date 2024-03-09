from rest_framework import serializers
from .models import Ilm, Jaam

class IlmSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Ilm
        fields = '__all__'


class JaamSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Jaam
        fields = '__all__'


