from rest_framework import serializers
from rest_framework.relations import HyperlinkedIdentityField, PrimaryKeyRelatedField
from rest_framework.reverse import reverse
from django.contrib.auth.models import User
from django.db.models import Field

from .models import (
    # Kroonika,
    Artikkel,
    Isik,
    Objekt,
    Organisatsioon,
    Pilt,
    Allikas,
    Viide
)


class ParameterisedHyperlinkedIdentityField(HyperlinkedIdentityField):
    """
    Represents the instance, or a property on the instance, using hyperlinking.

    lookup_fields is a tuple of tuples of the form:
        ('model_field', 'url_parameter')
    """
    lookup_fields = (('pk', 'pk'),)

    def __init__(self, *args, **kwargs):
        self.lookup_fields = kwargs.pop('lookup_fields', self.lookup_fields)
        super(ParameterisedHyperlinkedIdentityField, self).__init__(*args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        kwargs = {}
        for model_field, url_param in self.lookup_fields:
            attr = obj
            for field in model_field.split('.'):
                attr = getattr(attr,field)
            kwargs[url_param] = attr
        return reverse(view_name, kwargs=kwargs, request=request, format=format)


# TODO: Korrektselt ei tööta, "permissions-detail" ei leita
class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name')


# class KroonikaSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = Kroonika
#         fields = '__all__'


class PiltSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Pilt
        fields = '__all__'


class PiltListingField(serializers.RelatedField):
    def to_representation(self, value):
        return {'pk': value.pk, 'link': value.pilt.url}


class ArtikkelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    link = serializers.SerializerMethodField()
    url = ParameterisedHyperlinkedIdentityField(
        view_name='wiki:wiki_artikkel_detail',
        lookup_fields=(('pk', 'pk'), ('slug', 'slug'))
    )
    dob = serializers.SerializerMethodField()
    yob = serializers.SerializerMethodField()
    kirjeldus_lyhike = serializers.SerializerMethodField()

    pildid = PiltListingField(
        many=True,
        read_only=True,
    )

    def get_link(self, obj):
        return obj.get_absolute_url()
    
    def get_dob(self, obj):
        return obj.dob
    
    def get_yob(self, obj):
        return obj.yob
    
    def get_kirjeldus_lyhike(self, obj):
        return obj.kirjeldus_lyhike

    class Meta:
        model = Artikkel
        # fields = '__all__'
        exclude = ('lehekylg', 'kroonika',) # TODO:Kuni Kroonika kõrvaldamiseni


class IsikSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    link = serializers.SerializerMethodField()
    url = ParameterisedHyperlinkedIdentityField(
        view_name='wiki:wiki_isik_detail',
        lookup_fields=(('pk', 'pk'), ('slug', 'slug'))
    )
    # pilt_set = PiltListingField(
    #     many = True,
    #     read_only=True,
    # )
    pildid = PiltListingField(
        many=True,
        read_only=True,
    )

    def get_link(self, obj):
        return obj.get_absolute_url()

    class Meta:
        model = Isik
        fields = '__all__'
        # lookup_field = 'slug'
        # extra_kwargs = {
        #     'url': {'lookup_field': 'slug'}
        # }

class ObjektSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    link = serializers.SerializerMethodField()
    url = ParameterisedHyperlinkedIdentityField(
        view_name='wiki:wiki_objekt_detail',
        lookup_fields=(('pk', 'pk'), ('slug', 'slug'))
    )
    # pilt_set = PiltListingField(
    #     many=True,
    #     read_only=True,
    # )
    pildid = PiltListingField(
        many=True,
        read_only=True,
    )

    def get_link(self, obj):
        return obj.get_absolute_url()

    class Meta:
        model = Objekt
        fields = '__all__'


class OrganisatsioonSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    link = serializers.SerializerMethodField()
    url = ParameterisedHyperlinkedIdentityField(
        view_name='wiki:wiki_organisatsioon_detail',
        lookup_fields=(('pk', 'pk'), ('slug', 'slug'))
    )
    # pilt_set = PiltListingField(
    #     many=True,
    #     read_only=True,
    # )
    pildid = PiltListingField(
        many=True,
        read_only=True,
    )

    def get_link(self, obj):
        return obj.get_absolute_url()

    class Meta:
        model = Organisatsioon
        fields = '__all__'


class AllikasSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Allikas
        fields = '__all__'


class ViideSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Viide
        fields = '__all__'