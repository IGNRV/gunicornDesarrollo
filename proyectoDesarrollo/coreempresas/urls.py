# ./coreempresas/urls.py

from django.urls import path, include
from rest_framework import routers
from .views import EmpresaViewSet

router = routers.DefaultRouter()
router.register(r'empresa', EmpresaViewSet, basename='empresa')

urlpatterns = [
    path('', include(router.urls)),
]
