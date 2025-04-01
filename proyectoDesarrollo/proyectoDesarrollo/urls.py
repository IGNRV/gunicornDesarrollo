# ./proyectoDesarrollo/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Rutas de tasks
    path('tasks/', include('tasks.urls')),
    # Rutas de configuracion
    path('configuracion/', include('configuracion.urls')),
    # Rutas de operadores (lo nuevo)
    path('operadores/', include('operadores.urls')),
]
