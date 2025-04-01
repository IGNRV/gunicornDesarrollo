# Generated by Django 5.1.7 on 2025-03-28 13:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('coreempresas', '0001_initial'),
        ('operadores', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operacion', models.CharField(max_length=30)),
                ('detalle', models.TextField()),
                ('script', models.CharField(max_length=100)),
                ('tabla', models.CharField(max_length=100)),
                ('fecha', models.DateTimeField()),
                ('cliente_id', models.IntegerField(default=0)),
                ('contrato_id', models.IntegerField(default=0)),
                ('suscriptor_id', models.IntegerField(default=0)),
                ('empresa', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='coreempresas.empresa')),
                ('operador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='operadores.operador')),
            ],
            options={
                'db_table': '"dm_sistema"."log"',
                'indexes': [models.Index(fields=['cliente_id'], name='idx_log_cliente_id'), models.Index(fields=['contrato_id'], name='idx_log_contrato_id'), models.Index(fields=['empresa'], name='idx_log_empresa_id')],
            },
        ),
    ]
