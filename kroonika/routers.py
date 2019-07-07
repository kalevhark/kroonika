from rest_framework import routers

from wiki.viewsets import (
    UserViewSet,
    # KroonikaViewSet,
    ArtikkelViewSet,
    IsikViewSet,
    OrganisatsioonViewSet,
    ObjektViewSet,
    PiltViewSet,
    ViideViewSet,
)

router = routers.DefaultRouter()
router.register(r'user', UserViewSet)
# router.register(r'kroonika', KroonikaViewSet)
router.register(r'artikkel', ArtikkelViewSet)
router.register(r'isik', IsikViewSet)
router.register(r'organisatsioon', OrganisatsioonViewSet)
router.register(r'objekt', ObjektViewSet)
router.register(r'pilt', PiltViewSet)
router.register(r'viide', ViideViewSet)