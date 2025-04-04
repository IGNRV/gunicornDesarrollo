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
import secrets  # Para generar hashes aleatorios (cod_verificacion)
import requests  # Para enviar el correo replicando la lógica del cURL en PHP


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


class OperadorViewSet(viewsets.ModelViewSet):
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
            # 1) Verificamos si existe el Operador con esos datos.
            op = Operador.objects.get(operador_id=operador_id, clear=clear)

            # 2) Construimos un diccionario de respuesta limitado al 'operador_id'.
            response_data = {"operador_id": op.operador_id}

            # 3) Generamos el token JWT.
            payload = {
                'id': op.id,
                'operador_id': op.operador_id,
                # Expira en 24 horas.
                'exp': datetime.utcnow() + timedelta(hours=24)
            }
            token_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            # 4) Insertar registro en "sesiones" (modelo Sesion).
            ip_address = request.META.get('REMOTE_ADDR', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
            if ',' in ip_address:
                ip_address = ip_address.split(',')[0].strip()

            nueva_sesion = Sesion.objects.create(
                ip=ip_address,
                fecha=timezone.now(),
                operador_id=op.operador_id,
                empresa=op.empresa
            )

            # 5) Insertar una NUEVA fila en "sesiones_activas" (sin eliminar filas previas).
            # Generamos un hash aleatorio para cod_verificacion.
            random_hash = secrets.token_hex(16)
            SesionActiva.objects.create(
                operador_id=op.operador_id,
                sesion_id=str(nueva_sesion.id),
                fecha_registro=timezone.now(),
                empresa=op.empresa,
                token=token_jwt,
                cod_verificacion=random_hash
            )

            # 6) Enviamos el correo con el hash al correo (se asume que 'operador_id' es el email).
            asunto = "Código de Verificación"
            detalle_mail = f"Hola, tu código de verificación es: {random_hash}"
            enviar_correo_python("DM", op.operador_id, asunto, detalle_mail)

            # 7) Devolvemos solo el operador_id sin enviar la cookie ni el token.
            return Response(response_data, status=status.HTTP_200_OK)

        except Operador.DoesNotExist:
            return Response(
                {"error": "No existe un operador con esos datos"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def verificar(self, request):
        """
        POST /operadores/operadores/verificar/
        Recibe 'operador_id' y 'cod_verificacion'. Se debe mantener únicamente la
        sesión activa con la fecha más reciente para ese operador.
        Si el 'cod_verificacion' coincide con el de la sesión más reciente,
        se eliminan todas las demás filas (las más antiguas) para ese 'operador_id',
        se envía la cookie con el token de la sesión más reciente y se devuelve un código 200.
        Adicionalmente, se devuelven los siguientes datos del operador:
          - operador_id, rut, nombres, apellido_paterno, apellido_materno, modificable,
            email, estado, acceso_web, operador_administrador, grupo, empresa, superadmin, fecha_creacion.
        """
        operador_id = request.data.get('operador_id')
        cod_verificacion = request.data.get('cod_verificacion')
        if not operador_id or not cod_verificacion:
            return Response(
                {"error": "Se requieren 'operador_id' y 'cod_verificacion'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtenemos las sesiones activas para el operador, ordenadas de forma descendente por fecha_registro
        sesiones = SesionActiva.objects.filter(
            operador_id=operador_id
        ).order_by('-fecha_registro')

        if not sesiones.exists():
            return Response(
                {"error": "No se encontró ninguna sesión activa para este operador."},
                status=status.HTTP_404_NOT_FOUND
            )

        # La sesión más reciente:
        sesion_reciente = sesiones.first()

        if sesion_reciente.cod_verificacion != cod_verificacion:
            return Response(
                {"error": "El código de verificación no coincide con la sesión activa más reciente."},
                status=status.HTTP_400_BAD_REQUEST
            )

        token_jwt = sesion_reciente.token

        # Eliminamos todas las sesiones activas para este operador, excepto la más reciente.
        SesionActiva.objects.filter(operador_id=operador_id).exclude(id=sesion_reciente.id).delete()

        # Obtenemos los datos del operador.
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

        # Preparamos la respuesta, seteamos la cookie con el token de la sesión más reciente y retornamos.
        response_data = {
            "message": "Verificación exitosa.",
            "operador": operator_data
        }
        response = Response(response_data, status=status.HTTP_200_OK)
        response.set_cookie(
            key='token',
            value=token_jwt,
            httponly=True,
            secure=True,       # Ajustar a True en producción con HTTPS.
            max_age=24 * 3600,
            samesite='None'
        )
        return response

    @action(detail=False, methods=['get'])
    def logout(self, request):
        """
        GET /operadores/logout/
        - Toma la cookie 'token' y elimina la fila en sesiones_activas cuyo token coincida.
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


class OperadorByTokenViewSet(viewsets.ViewSet):
    """
    Sólo permite obtener la sesión activa leyendo la cookie 'token':
    GET /operadores/sesiones-activas-token/  (sin <token>)
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

        # Se serializa la sesión activa
        sesion_activa_data = SesionActivaSerializer(sesion_activa).data

        # Buscamos al operador cuyos datos coincidan con "operador_id" en SesionActiva
        try:
            op = Operador.objects.get(operador_id=sesion_activa.operador_id)
        except Operador.DoesNotExist:
            return Response(
                {"error": "No se encontró el operador relacionado a esta sesión activa."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Se serializa el operador para incluir todas sus columnas
        operador_data = OperadorSerializer(op).data

        # Combinamos ambos en la misma respuesta
        combined_data = {
            "sesion_activa": sesion_activa_data,
            "operador_data": operador_data
        }

        return Response(combined_data, status=status.HTTP_200_OK)
