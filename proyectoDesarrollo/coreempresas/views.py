# ./coreempresas/views.py

from rest_framework import viewsets
from .models import Empresa
from .serializer import EmpresaSerializer
from django.shortcuts import render

# ViewSet para el modelo Empresa que permite listar, crear, actualizar y eliminar.
class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
