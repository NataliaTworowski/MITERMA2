@echo off
REM Script para ejecutar el comando de emails de finalizacion
REM Configurar este archivo para ejecutarse cada 10-15 minutos

cd /d "C:\Users\natal\OneDrive\Escritorio\Proyecto_titulo\MITERMA2"

REM Activar entorno virtual si usas uno (descomenta la línea de abajo)
REM call venv\Scripts\activate

REM Ejecutar el comando
python manage.py enviar_emails_finalizacion

REM Log simple (opcional)
echo %date% %time% - Comando ejecutado >> logs\email_finalizacion.log