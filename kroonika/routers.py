from rest_framework import routers
from wiki.viewsets import (
    UserViewSet,
    KroonikaViewSet,
    ArtikkelViewSet,
    IsikViewSet,
    ObjektViewSet,
    OrganisatsioonViewSet,
    ObjektViewSet,
    PiltViewSet
)

router = routers.DefaultRouter()
router.register(r'user', UserViewSet)
router.register(r'kroonika', KroonikaViewSet)
router.register(r'artikkel', ArtikkelViewSet)
router.register(r'isik', IsikViewSet)
router.register(r'organisatsioon', OrganisatsioonViewSet)
router.register(r'objekt', ObjektViewSet)
router.register(r'pilt', PiltViewSet)