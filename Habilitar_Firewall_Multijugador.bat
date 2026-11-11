@echo off
title Habilitar Firewall para Batallas del TEC
echo ======================================================================
echo    CONFIGURACION DE FIREWALL - BATALLAS DEL TEC MULTIJUGADOR
echo ======================================================================
echo.
echo Comprobando permisos de Administrador...
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [SOLICITANDO ELEVACION...] Por favor acepta el cuadro de Administrador.
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\" admin' -Verb RunAs"
    exit /b
)

echo [OK] Permisos de Administrador concedidos.
echo.
echo Abriendo puerto TCP 5000 en el Firewall de Windows...
netsh advfirewall firewall delete rule name="BatallasTEC_Port5000" >nul 2>&1
netsh advfirewall firewall add rule name="BatallasTEC_Port5000" dir=in action=allow protocol=TCP localport=5000

echo.
echo Abriendo puerto TCP 5001 en el Firewall de Windows...
netsh advfirewall firewall delete rule name="BatallasTEC_Port5001" >nul 2>&1
netsh advfirewall firewall add rule name="BatallasTEC_Port5001" dir=in action=allow protocol=TCP localport=5001

echo.
echo ======================================================================
echo  LISTO! Los puertos 5000 y 5001 ya estan permitidos para multijugador.
echo  Ahora puedes conectar dos computadoras sin bloqueos de Windows.
echo ======================================================================
echo.
pause
