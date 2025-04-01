# Generated by Django 5.1.7 on 2025-03-28 13:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('coreempresas', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Menu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.CharField(max_length=50)),
                ('texto', models.CharField(default='', max_length=50)),
                ('etiqueta', models.CharField(blank=True, max_length=50, null=True)),
                ('descripcion', models.CharField(max_length=255)),
                ('nivel_menu', models.IntegerField(default=3)),
                ('orden', models.IntegerField(blank=True, null=True)),
                ('modificable', models.CharField(default='SI', max_length=2)),
                ('separador_up', models.IntegerField(default=0)),
            ],
            options={
                'db_table': '"dm_sistema"."menus"',
            },
        ),
        migrations.CreateModel(
            name='Modulo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modulo', models.CharField(max_length=50)),
                ('nombre', models.CharField(max_length=255)),
                ('nombre_menu', models.CharField(blank=True, max_length=100, null=True)),
                ('estado', models.SmallIntegerField(blank=True, null=True)),
                ('icon', models.CharField(blank=True, max_length=255, null=True)),
                ('orden', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': '"dm_sistema"."modulos"',
            },
        ),
        migrations.CreateModel(
            name='EmpresaModulo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.IntegerField(default=1)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='empresa_modulos', to='coreempresas.empresa')),
                ('modulo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='empresa_modulos', to='configuracion.modulo')),
            ],
            options={
                'db_table': '"dm_sistema"."empresa_modulos"',
            },
        ),
        migrations.CreateModel(
            name='EmpresaModuloMenu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('empresa_modulo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='menus', to='configuracion.empresamodulo')),
                ('menu', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='empresa_modulos_menus', to='configuracion.menu')),
            ],
            options={
                'db_table': '"dm_sistema"."empresa_modulos_menu"',
            },
        ),
        migrations.AddField(
            model_name='menu',
            name='modulo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='menus', to='configuracion.modulo'),
        ),
    ]
