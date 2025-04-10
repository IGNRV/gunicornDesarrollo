# ./proyectoDesarrollo/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Se incluye el módulo de URLs de coreempresas con el prefijo "coreempresas/"
    path('coreempresas/', include('coreempresas.urls')),
    # Se incluyen las demás apps de forma similar (ejemplo)
    path('configuracion/', include('configuracion.urls')),
    path('operadores/', include('operadores.urls')),
    path('tasks/', include('tasks.urls')),
]
