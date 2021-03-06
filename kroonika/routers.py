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
    JaamViewSet)

router = routers.DefaultRouter()

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
