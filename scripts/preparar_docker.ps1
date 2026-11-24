<#
.SYNOPSIS
Habilita WSL2 y levanta el stack de Jarvis con Docker Compose.

.DESCRIPTION
Se ejecuta en dos pasos:
  1) Sin -PostReboot: habilita WSL2, actualiza el kernel y pregunta si reiniciar.
  2) Tras el reinicio (o con -PostReboot): arranca Docker Desktop, espera al
     motor, levanta el compose y configura la instancia de Evolution API.

Debe ejecutarse con PowerShell como Administrador; si no lo está, solicita elevación.
#>
param(
    [switch]$PostReboot,
    [string]$DockerPath = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
)

$ErrorActionPreference = 'Stop'

function Test-Admin {
    $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-FeatureState([string]$nombre) {
    $feature = Get-WindowsOptionalFeature -Online -FeatureName $nombre -ErrorAction SilentlyContinue
    if ($null -eq $feature) { return 'Desconocido' }
    return [string]$feature.State
}

if (-not (Test-Admin)) {
    Write-Host 'Se necesitan permisos de administrador; solicitando elevacion...' -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`""
    ) -Wait
    exit 0
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
Write-Host "Directorio del proyecto: $root"

if (-not $PostReboot) {
    $estadoWsl = Get-FeatureState 'Microsoft-Windows-Subsystem-Linux'
    $estadoVm = Get-FeatureState 'VirtualMachinePlatform'
    Write-Host "WSL: $estadoWsl | VirtualMachinePlatform: $estadoVm"

    if ($estadoWsl -ne 'Enabled' -or $estadoVm -ne 'Enabled') {
        Write-Host 'Habilitando caracteristicas de WSL2...' -ForegroundColor Cyan
        dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
        dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
        wsl --update
        wsl --install --no-distribution

        Write-Host 'Es necesario reiniciar el equipo.' -ForegroundColor Yellow
        $respuesta = Read-Host '¿Reiniciar ahora? (s/n)'
        if ($respuesta -match '^[sS]') {
            Restart-Computer -Force
        }
        else {
            Write-Host 'Reinicia cuando puedas y vuelve a ejecutar este mismo script.'
            exit 0
        }
        exit 0
    }
    $PostReboot = $true
}

if (-not (Test-Path $DockerPath)) {
    throw "No se encontro Docker Desktop en: $DockerPath"
}

if (-not (Get-Process 'Docker Desktop' -ErrorAction SilentlyContinue)) {
    $iniciador = Join-Path (Split-Path -Parent (Split-Path -Parent $DockerPath)) 'Docker Desktop.exe'
    Write-Host 'Iniciando Docker Desktop...' -ForegroundColor Cyan
    Start-Process $iniciador
}

Write-Host 'Esperando al motor de Docker (hasta 3 minutos)...' -ForegroundColor Cyan
$listo = $false
for ($intento = 0; $intento -lt 36; $intento++) {
    Start-Sleep -Seconds 5
    & $DockerPath info --format '{{.ServerVersion}}' 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $listo = $true
        break
    }
}
if (-not $listo) {
    throw 'El motor de Docker no arranco. Revisa Docker Desktop y sus logs.'
}

Write-Host 'Motor listo. Levantando el stack...' -ForegroundColor Cyan
& $DockerPath compose up -d --build
if ($LASTEXITCODE -ne 0) { throw 'docker compose up fallo.' }

& $DockerPath compose ps

Write-Host 'Configurando instancia de Evolution API y QR...' -ForegroundColor Cyan
python scripts/setup_evolution.py --base-url http://localhost:8080

Write-Host 'Listo. Revisa data/qr.png y el estado con: docker compose logs -f backend' -ForegroundColor Green
