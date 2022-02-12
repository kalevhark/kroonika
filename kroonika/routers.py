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
)

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
