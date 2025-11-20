# Script PowerShell para crear la tarea programada automáticamente
# Ejecutar este script como administrador

$TaskName = "MiTerma-Email-Finalizacion"
$ScriptPath = "C:\Users\natal\OneDrive\Escritorio\Proyecto_titulo\MITERMA2\ejecutar_emails_finalizacion.bat"

# Eliminar tarea existente si existe
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Tarea existente eliminada."
}

# Crear nueva tarea
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -Daily -At "00:00"
$Trigger.Repetition = New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 1)

$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Envía emails de finalización de entradas cada 10 minutos"

Write-Host "Tarea '$TaskName' creada exitosamente."
Write-Host "Se ejecutará cada 10 minutos para enviar emails de finalización."