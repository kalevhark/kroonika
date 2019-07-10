from rest_framework import serializers
from django.contrib.auth.models import User

from .models import (
    # Kroonika,
    Artikkel,
    Isik,
    Objekt,
    Organisatsioon,
    Pilt,
    Viide
)

# TODO: Korrektselt ei tööta, "permissions-detail" ei leita
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name')


# class KroonikaSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = Kroonika
#         fields = '__all__'


class ArtikkelSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Artikkel
        # fields = '__all__'
        exclude = ('lehekylg', 'kroonika',) # TODO:Kuni Kroonika kõrvaldamiseni


class IsikSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Isik
        fields = '__all__'


class ObjektSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Objekt
        fields = '__all__'


class OrganisatsioonSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Organisatsioon
        fields = '__all__'


class PiltSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Pilt
        fields = '__all__'


class ViideSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Viide
        fields = '__all__'