from django.utils.safestring import mark_safe

from rest_framework import routers

from wiki.viewsets import (
    UserViewSet,
    # KroonikaViewSet,
    ArtikkelViewSet,
    IsikViewSet,
    OrganisatsioonViewSet,
    ObjektViewSet,
    PiltViewSet,
    AllikasViewSet,
    ViideViewSet,
)

from ilm.viewsets import (
    IlmViewSet,
    JaamViewSet,
    # ForecastsViewSet
)

# from rest_framework.routers import Route, DynamicRoute, SimpleRouter

# class CustomReadOnlyRouter(SimpleRouter):
#     """
#     A router for read-only APIs, which doesn't use trailing slashes.
#     """
#     routes = [
#         Route(
#             url=r'^{prefix}$',
#             mapping={'get': 'list'},
#             name='{basename}-list',
#             detail=False,
#             initkwargs={'suffix': 'List'}
#         ),
#         Route(
#             url=r'^{prefix}/{lookup}$',
#             mapping={'get': 'retrieve'},
#             name='{basename}-detail',
#             detail=True,
#             initkwargs={'suffix': 'Detail'}
#         ),
#         DynamicRoute(
#             url=r'^{prefix}/{lookup}/{url_path}$',
#             name='{basename}-{url_name}',
#             detail=True,
#             initkwargs={}
#         )
#     ]


class MyAPIRootView(routers.APIRootView):
    """
    Controls appearance of the API root view
    """

    def get_view_name(self) -> str:
        return "valgalinn.ee API"

    def get_view_description(self, html=False) -> str:
        text = "Valga linna kroonika REST API"
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text


class MyRouter(routers.DefaultRouter):
    APIRootView = MyAPIRootView

# router = routers.DefaultRouter()
# router = CustomReadOnlyRouter()
router = MyRouter()

# wiki
router.register(r'user', UserViewSet)
# router.register(r'kroonika', KroonikaViewSet)
router.register(r'artikkel', ArtikkelViewSet)
router.register(r'isik', IsikViewSet)
router.register(r'organisatsioon', OrganisatsioonViewSet)
router.register(r'objekt', ObjektViewSet)
router.register(r'pilt', PiltViewSet)
router.register(r'allikas', AllikasViewSet)
router.register(r'viide', ViideViewSet)

# ilm
router.register(r'i', IlmViewSet)
router.register(r'j', JaamViewSet)
# router.register(r'forecasts', ForecastsViewSet)

# router.get_api_root_view().cls.__name__ = "valgalinn.ee API"
# router.get_api_root_view().cls.__doc__ = "API päringute tegemiseks Valga linna kroonika andmebaasist"