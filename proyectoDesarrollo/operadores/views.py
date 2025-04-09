# ./operadores/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Operador, OperadorBodega, OperadorEmpresaModulo,
    OperadorEmpresaModuloMenu, OperadorGrupo, OperadorPuntoVenta,
    Sesion, SesionActiva
    # SesionEjecutivo ya NO existe
)
from .serializer import (
    OperadorSerializer, OperadorBodegaSerializer, OperadorEmpresaModuloSerializer,
    OperadorEmpresaModuloMenuSerializer, OperadorGrupoSerializer, OperadorPuntoVentaSerializer,
    SesionSerializer, SesionActivaSerializer
    # SesionEjecutivoSerializer eliminado
)

import jwt
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone
import secrets  # Para generar hashes aleatorios (cod_verificacion)
import requests  # Para enviar el correo replicando la lógica del cURL en PHP

# Se agrega la importación para poder ejecutar consultas SQL crudas
from django.db import connection
from django.http import HttpResponseForbidden


class RestrictToReactMixin:
    ALLOWED_ORIGIN = "http://localhost:5173"  # Cambia por el dominio real de tu aplicación React

    def initial(self, request, *args, **kwargs):
        origin = request.META.get("HTTP_ORIGIN")
        if origin != self.ALLOWED_ORIGIN:
            return HttpResponseForbidden("Acceso denegado.")
        return super().initial(request, *args, **kwargs)


def enviar_correo_python(remitente, correo_destino, asunto, detalle):
    """
    Función que replica la lógica del PHP para enviar correo.
    Realiza un POST a http://mail.smartgest.cl/mailserver/server_mail.php
    con los parámetros requeridos.
    """
    data = {
        "destino": correo_destino,
        "asunto": asunto,
        "detalle": detalle,
        "from": remitente
    }
    try:
        resp = requests.post("http://mail.smartgest.cl/mailserver/server_mail.php", data=data)
        # Opcional: se puede revisar resp.status_code, etc.
    except Exception as e:
        print(f"Error al enviar el correo: {e}")


class OperadorViewSet(RestrictToReactMixin, viewsets.ModelViewSet):
    queryset = Operador.objects.all()
    serializer_class = OperadorSerializer

    @action(detail=False, methods=['post'])
    def validar(self, request):
        """
        POST /operadores/operadores/validar/
        Valida que 'operador_id' y 'clear' existan en la tabla 'operador'.
        Si la validación es correcta:
         - Se inserta una nueva fila en 'sesiones_activas' con token y cod_verificacion.
         - Se envía un correo al 'operador_id' (se asume que es el email) con el hash generado.
         - Se devuelve solo un código 200 y el valor de 'operador_id'.
        """
        operador_id = request.data.get('operador_id')
        clear = request.data.get('clear')
        if not operador_id or not clear:
            return Response(
                {"error": "Se requieren 'operador_id' y 'clear'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            op = Operador.objects.get(operador_id=operador_id, clear=clear)

            response_data = {"operador_id": op.operador_id}

            payload = {
                'id': op.id,
                'operador_id': op.operador_id,
                'exp': datetime.utcnow() + timedelta(hours=24)
            }
            token_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            ip_address = request.META.get('REMOTE_ADDR', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
            if ',' in ip_address:
                ip_address = ip_address.split(',')[0].strip()

            nueva_sesion = Sesion.objects.create(
                ip=ip_address,
                fecha=timezone.now(),
                operador_id=op.operador_id,
                empresa=op.empresa
            )

            random_hash = secrets.token_hex(16)
            SesionActiva.objects.create(
                operador_id=op.operador_id,
                sesion_id=str(nueva_sesion.id),
                fecha_registro=timezone.now(),
                empresa=op.empresa,
                token=token_jwt,
                cod_verificacion=random_hash
            )

            asunto = "Código de Verificación"
            detalle_mail = f"Hola, tu código de verificación es: {random_hash}"
            enviar_correo_python("DM", op.operador_id, asunto, detalle_mail)

            return Response(response_data, status=status.HTTP_200_OK)

        except Operador.DoesNotExist:
            # --------------------------------------------------------------------------------
            # AÑADIDO: Si existe un Operador con ese ID pero la 'clear' es incorrecta,
            #          incrementamos conexion_fallida en 1.
            # --------------------------------------------------------------------------------
            try:
                op_incorrecto = Operador.objects.get(operador_id=operador_id)
                op_incorrecto.conexion_fallida += 1
                op_incorrecto.save()
            except Operador.DoesNotExist:
                pass  # Si ni siquiera existe el operador_id, no hacemos nada
            # --------------------------------------------------------------------------------

            return Response(
                {"error": "No existe un operador con esos datos"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def verificar(self, request):
        """
        POST /operadores/operadores/verificar/
        Recibe 'operador_id' y 'cod_verificacion'. Se debe mantener únicamente la
        sesión activa más reciente para ese operador.
        Si el 'cod_verificacion' coincide con la de la sesión más reciente:
         - Se eliminan todas las demás filas.
         - Se envía la cookie con el token de la sesión.
         - Se retorna un código 200 con datos del operador (incluyendo "modulos" inmediatamente).
        """
        operador_id = request.data.get('operador_id')
        cod_verificacion = request.data.get('cod_verificacion')
        if not operador_id or not cod_verificacion:
            return Response(
                {"error": "Se requieren 'operador_id' y 'cod_verificacion'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        sesiones = SesionActiva.objects.filter(
            operador_id=operador_id
        ).order_by('-fecha_registro')

        if not sesiones.exists():
            return Response(
                {"error": "No se encontró ninguna sesión activa para este operador."},
                status=status.HTTP_404_NOT_FOUND
            )

        sesion_reciente = sesiones.first()

        if sesion_reciente.cod_verificacion != cod_verificacion:
            return Response(
                {"error": "El código de verificación no coincide con la sesión activa más reciente."},
                status=status.HTTP_400_BAD_REQUEST
            )

        token_jwt = sesion_reciente.token

        # Eliminar todas las demás sesiones activas excepto la más reciente
        SesionActiva.objects.filter(operador_id=operador_id).exclude(id=sesion_reciente.id).delete()

        try:
            op = Operador.objects.get(operador_id=operador_id)
        except Operador.DoesNotExist:
            return Response(
                {"error": "No se encontró el operador."},
                status=status.HTTP_404_NOT_FOUND
            )

        operator_data = {
            "operador_id": op.operador_id,
            "rut": op.rut,
            "nombres": op.nombres,
            "apellido_paterno": op.apellido_paterno,
            "apellido_materno": op.apellido_materno,
            "modificable": op.modificable,
            "email": op.email,
            "estado": op.estado,
            "acceso_web": op.acceso_web,
            "operador_administrador": op.operador_administrador,
            "grupo": op.grupo.id if op.grupo else None,
            "empresa": op.empresa.id if op.empresa else None,
            "superadmin": op.superadmin,
            "fecha_creacion": op.fecha_creacion
        }

        # -------------------------------------------------------------------
        # AÑADIMOS AQUÍ la consulta que antes se veía solo en "get_by_cookie"
        # De esta manera, en cuanto se verifica y se setea la cookie,
        # retornamos inmediatamente la información de "modulos".
        # -------------------------------------------------------------------
        modulos = []
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.nombre_menu, b.id, c.icon
                FROM dm_sistema.operador_empresa_modulos AS a
                JOIN dm_sistema.empresa_modulos AS b ON a.empresa_modulo_id = b.id
                JOIN dm_sistema.modulos AS c ON b.modulo_id = c.id
                WHERE a.operador_id = %s
                  AND b.estado = 1
                  AND c.estado = 1
                  AND b.empresa_id = %s
                ORDER BY c.orden
            """, [op.id, op.empresa.id])
            rows = cursor.fetchall()
            for row in rows:
                modulos.append({
                    "nombre_menu": row[0],
                    "id": row[1],
                    "icon": row[2]
                })
        # -------------------------------------------------------------------

        response_data = {
            "message": "Verificación exitosa.",
            "operador": operator_data,
            "modulos": modulos  # <-- Se devuelven los módulos también
        }
        response = Response(response_data, status=status.HTTP_200_OK)
        response.set_cookie(
            key='token',
            value=token_jwt,
            httponly=True,
            secure=True,
            max_age=24 * 3600,
            samesite='None'
        )
        return response

    @action(detail=False, methods=['get'])
    def logout(self, request):
        """
        GET /operadores/logout/
        - Elimina la fila en sesiones_activas cuyo token coincida con la cookie 'token'.
        """
        token_cookie = request.COOKIES.get('token')
        if not token_cookie:
            return Response(
                {"error": "No se encontró la cookie 'token' en la solicitud."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            sesion_activa = SesionActiva.objects.get(token=token_cookie)
        except SesionActiva.DoesNotExist:
            return Response(
                {"error": "El token de la cookie no coincide con ninguna sesión activa."},
                status=status.HTTP_404_NOT_FOUND
            )

        sesion_activa.delete()
        response = Response({"message": "Sesión eliminada correctamente."}, status=status.HTTP_200_OK)
        response.delete_cookie('token')
        return response


class OperadorBodegaViewSet(RestrictToReactMixin, viewsets.ModelViewSet):
    queryset = OperadorBodega.objects.all()
    serializer_class = OperadorBodegaSerializer


class OperadorEmpresaModuloViewSet(RestrictToReactMixin, viewsets.ModelViewSet):
    queryset = OperadorEmpresaModulo.objects.all()
    serializer_class = OperadorEmpresaModuloSerializer


class OperadorEmpresaModuloMenuViewSet(RestrictToReactMixin, viewsets.ModelViewSet):
    queryset = OperadorEmpresaModuloMenu.objects.all()
    serializer_class = OperadorEmpresaModuloMenuSerializer


class OperadorGrupoViewSet(RestrictToReactMixin, viewsets.ModelViewSet):
    queryset = OperadorGrupo.objects.all()
    serializer_class = OperadorGrupoSerializer


class OperadorPuntoVentaViewSet(RestrictToReactMixin, viewsets.ModelViewSet):
    queryset = OperadorPuntoVenta.objects.all()
    serializer_class = OperadorPuntoVentaSerializer


class SesionViewSet(RestrictToReactMixin, viewsets.ModelViewSet):
    queryset = Sesion.objects.all()
    serializer_class = SesionSerializer


class SesionActivaViewSet(RestrictToReactMixin, viewsets.ModelViewSet):
    queryset = SesionActiva.objects.all()
    serializer_class = SesionActivaSerializer


# Se elimina la clase SesionEjecutivoViewSet


class OperadorByTokenViewSet(RestrictToReactMixin, viewsets.ViewSet):
    """
    GET /operadores/sesiones-activas-token/
    Obtiene la sesión activa leyendo la cookie 'token'.
    """
    def get_by_cookie(self, request):
        token_cookie = request.COOKIES.get('token')
        if not token_cookie:
            return Response({"error": "No se encontró la cookie 'token' en la solicitud."},
                            status=status.HTTP_401_UNAUTHORIZED)
        try:
            sesion_activa = SesionActiva.objects.get(token=token_cookie)
        except SesionActiva.DoesNotExist:
            return Response({"error": "El token en la cookie no coincide con ninguna sesión activa."},
                            status=status.HTTP_404_NOT_FOUND)

        sesion_activa_data = SesionActivaSerializer(sesion_activa).data

        try:
            op = Operador.objects.get(operador_id=sesion_activa.operador_id)
        except Operador.DoesNotExist:
            return Response(
                {"error": "No se encontró el operador relacionado a esta sesión activa."},
                status=status.HTTP_404_NOT_FOUND
            )

        operador_data = OperadorSerializer(op).data

        # ----------------------------------------------------
        # AQUI SE AGREGA LA CONSULTA SQL USANDO EL ID DEL OPERADOR Y LA EMPRESA
        # operador_data['id'] -> coincide con 'a.operador_id'
        # operador_data['empresa'] -> coincide con 'b.empresa_id'
        # ----------------------------------------------------
        modulos = []
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.nombre_menu, b.id, c.icon
                FROM dm_sistema.operador_empresa_modulos AS a
                JOIN dm_sistema.empresa_modulos AS b ON a.empresa_modulo_id = b.id
                JOIN dm_sistema.modulos AS c ON b.modulo_id = c.id
                WHERE a.operador_id = %s
                  AND b.estado = 1
                  AND c.estado = 1
                  AND b.empresa_id = %s
                ORDER BY c.orden
            """, [operador_data['id'], operador_data['empresa']])
            rows = cursor.fetchall()
            for row in rows:
                modulos.append({
                    "nombre_menu": row[0],
                    "id": row[1],
                    "icon": row[2]
                })

        # Se agregan los resultados de la consulta en la respuesta
        combined_data = {
            "sesion_activa": sesion_activa_data,
            "operador_data": operador_data,
            "modulos": modulos
        }

        return Response(combined_data, status=status.HTTP_200_OK)
