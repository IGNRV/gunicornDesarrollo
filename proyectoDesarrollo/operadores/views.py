# ./operadores/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Operador, OperadorBodega, OperadorEmpresaModulo,
    OperadorEmpresaModuloMenu, OperadorGrupo, OperadorPuntoVenta,
    Sesion, SesionActiva, SesionEjecutivo
)
from .serializer import (
    OperadorSerializer, OperadorBodegaSerializer, OperadorEmpresaModuloSerializer,
    OperadorEmpresaModuloMenuSerializer, OperadorGrupoSerializer, OperadorPuntoVentaSerializer,
    SesionSerializer, SesionActivaSerializer, SesionEjecutivoSerializer
)

import jwt
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone

class OperadorViewSet(viewsets.ModelViewSet):
    queryset = Operador.objects.all()
    serializer_class = OperadorSerializer

    @action(detail=False, methods=['post'])
    def validar(self, request):
        operador_id = request.data.get('operador_id')
        clear = request.data.get('clear')
        if not operador_id or not clear:
            return Response(
                {"error": "Se requieren 'operador_id' y 'clear'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1) Verificamos si existe el Operador con esos datos
            op = Operador.objects.get(operador_id=operador_id, clear=clear)

            # 2) Construimos el diccionario con los campos del operador:
            data = {
                "operador_id": op.operador_id,
                "rut": op.rut,
                "nombres": op.nombres,
                "apellido_paterno": op.apellido_paterno,
                "apellido_materno": op.apellido_materno,
                "email": op.email,
                "estado": op.estado,
                "acceso_web": op.acceso_web,
                "conexion_fallida": op.conexion_fallida,
                "operador_administrador": op.operador_administrador,
                "grupo": op.grupo.id if op.grupo else None,
                "empresa": op.empresa.id if op.empresa else None,
                "superadmin": op.superadmin,
                "fecha_creacion": op.fecha_creacion
            }

            # 3) Generamos el token JWT
            payload = {
                'id': op.id,
                'operador_id': op.operador_id,
                # Expira en 24 horas
                'exp': datetime.utcnow() + timedelta(hours=24)
            }
            token_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            # 4) Insertar registro en "sesiones" (modelo Sesion)
            ip_address = request.META.get('REMOTE_ADDR', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
            if ',' in ip_address:
                ip_address = ip_address.split(',')[0].strip()

            nueva_sesion = Sesion.objects.create(
                ip=ip_address,
                fecha=timezone.now(),
                operador_id=op.operador_id,
                empresa=op.empresa
            )

            # 5) Insertar o actualizar registro en "sesiones_activas" (modelo SesionActiva)
            sesion_activa = SesionActiva.objects.filter(
                operador_id=op.operador_id,
                empresa=op.empresa
            ).first()

            if sesion_activa:
                # Actualizamos las columnas: sesion_id, fecha_registro y token
                sesion_activa.sesion_id = str(nueva_sesion.id)
                sesion_activa.fecha_registro = timezone.now()
                sesion_activa.token = token_jwt
                sesion_activa.save()
            else:
                # Creamos una nueva fila en sesiones_activas
                SesionActiva.objects.create(
                    operador_id=op.operador_id,
                    sesion_id=str(nueva_sesion.id),
                    fecha_registro=timezone.now(),
                    empresa=op.empresa,
                    token=token_jwt
                )

            # 6) Retornamos la info del operador, pero el token va por cookie HttpOnly
            response = Response(data, status=status.HTTP_200_OK)
            response.set_cookie(
                key='token',
                value=token_jwt,
                httponly=True,
                secure=True,       # Ponlo True si estás en HTTPS
                max_age=24 * 3600, # 24 horas
                samesite='None'    # o 'Strict' / 'Lax' según tu implementación
            )

            return response

        except Operador.DoesNotExist:
            return Response(
                {"error": "No existe un operador con esos datos"},
                status=status.HTTP_404_NOT_FOUND
            )

    # =========================================
    # NUEVO MÉTODO: GET /operadores/logout/
    # =========================================
    @action(detail=False, methods=['get'])
    def logout(self, request):
        """
        GET /operadores/logout/
        - Toma la cookie 'token' y elimina la fila en sesiones_activas cuyo token coincida.
        """
        # 1) Revisar la cookie "token"
        token_cookie = request.COOKIES.get('token')
        if not token_cookie:
            return Response(
                {"error": "No se encontró la cookie 'token' en la solicitud."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 2) Buscar la sesión activa con ese token
        try:
            sesion_activa = SesionActiva.objects.get(token=token_cookie)
        except SesionActiva.DoesNotExist:
            return Response(
                {"error": "El token de la cookie no coincide con ninguna sesión activa."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3) Eliminar la fila
        sesion_activa.delete()

        # 4) Opcional: eliminar la cookie del response
        response = Response({"message": "Sesión eliminada correctamente."}, status=status.HTTP_200_OK)
        response.delete_cookie('token')

        return response


class OperadorBodegaViewSet(viewsets.ModelViewSet):
    queryset = OperadorBodega.objects.all()
    serializer_class = OperadorBodegaSerializer


class OperadorEmpresaModuloViewSet(viewsets.ModelViewSet):
    queryset = OperadorEmpresaModulo.objects.all()
    serializer_class = OperadorEmpresaModuloSerializer


class OperadorEmpresaModuloMenuViewSet(viewsets.ModelViewSet):
    queryset = OperadorEmpresaModuloMenu.objects.all()
    serializer_class = OperadorEmpresaModuloMenuSerializer


class OperadorGrupoViewSet(viewsets.ModelViewSet):
    queryset = OperadorGrupo.objects.all()
    serializer_class = OperadorGrupoSerializer


class OperadorPuntoVentaViewSet(viewsets.ModelViewSet):
    queryset = OperadorPuntoVenta.objects.all()
    serializer_class = OperadorPuntoVentaSerializer


class SesionViewSet(viewsets.ModelViewSet):
    queryset = Sesion.objects.all()
    serializer_class = SesionSerializer


class SesionActivaViewSet(viewsets.ModelViewSet):
    queryset = SesionActiva.objects.all()
    serializer_class = SesionActivaSerializer


class SesionEjecutivoViewSet(viewsets.ModelViewSet):
    queryset = SesionEjecutivo.objects.all()
    serializer_class = SesionEjecutivoSerializer


# NUEVO: Vista para consultar datos de Operador a partir del token en la URL o en la cookie
class OperadorByTokenViewSet(viewsets.ViewSet):
    """
    GET /operadores/sesiones-activas-token/{token}/
    - Busca el registro en SesionActiva cuyo token coincida y retorna la información de SesionActiva.
    DELETE /operadores/sesiones-activas-token/{token}/
    - Elimina el registro en SesionActiva que tenga el token indicado.
    
    GET /operadores/sesiones-activas-token/ (sin <token>)
    - Toma el token desde la cookie "token" y retorna la información de SesionActiva si existe.
    """

    def retrieve(self, request, token=None):
        # 1) Buscar la sesión activa por el token
        try:
            sesion_activa = SesionActiva.objects.get(token=token)
        except SesionActiva.DoesNotExist:
            return Response({"error": "Token no encontrado en sesiones activas"}, status=status.HTTP_404_NOT_FOUND)

        # 2) Serializar la info de la SesionActiva y retornarla
        serializer = SesionActivaSerializer(sesion_activa)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, token=None):
        # 1) Buscar la sesión activa por el token
        try:
            sesion_activa = SesionActiva.objects.get(token=token)
        except SesionActiva.DoesNotExist:
            return Response({"error": "Token no encontrado en sesiones activas"}, status=status.HTTP_404_NOT_FOUND)

        # 2) Eliminarla y retornar respuesta
        sesion_activa.delete()
        return Response({"message": "Sesion activa eliminada correctamente."}, status=status.HTTP_204_NO_CONTENT)

    # NUEVA FUNCIÓN: GET sin token en la URL, se toma desde la cookie
    def get_by_cookie(self, request):
        # 1) Revisar la cookie "token"
        token_cookie = request.COOKIES.get('token')
        if not token_cookie:
            return Response({"error": "No se encontró la cookie 'token' en la solicitud."},
                            status=status.HTTP_401_UNAUTHORIZED)

        # 2) Buscar la sesión activa
        try:
            sesion_activa = SesionActiva.objects.get(token=token_cookie)
        except SesionActiva.DoesNotExist:
            return Response({"error": "El token en la cookie no coincide con ninguna sesión activa."},
                            status=status.HTTP_404_NOT_FOUND)

        # 3) Devolver la info de la SesionActiva
        serializer = SesionActivaSerializer(sesion_activa)
        return Response(serializer.data, status=status.HTTP_200_OK)
