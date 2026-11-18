param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("start", "status", "stop")]
    [string]$Action
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimePath = Join-Path $ProjectRoot "data\runtime"
$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

$OpcUaPidFile = Join-Path $RuntimePath "opcua-server.pid"
$GatewayPidFile = Join-Path $RuntimePath "gateway.pid"

# Separate signals enforce the shutdown order: Gateway first, OPC UA server second.
$GatewayStopSignal = Join-Path $RuntimePath "gateway.stop"
$OpcUaStopSignal = Join-Path $RuntimePath "opcua-server.stop"

$OpcUaLog = Join-Path $RuntimePath "opcua-server.log"
$GatewayLog = Join-Path $RuntimePath "gateway.log"

$OpcUaModule = "simulator.industrial_assets.opcua_server"
$GatewayModule = "edge.industrial_gateway.gateway"

$OpcUaPort = 4840
$MqttPort = 1883
$StartupTimeoutSeconds = 30
$ShutdownTimeoutSeconds = 20

function Initialize-Runtime {
    if (-not (Test-Path $RuntimePath)) {
        New-Item -ItemType Directory -Path $RuntimePath -Force |
        Out-Null
    }
}

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port
    )

    $Client = New-Object System.Net.Sockets.TcpClient

    try {
        $AsyncResult = $Client.BeginConnect(
            $HostName,
            $Port,
            $null,
            $null
        )

        if (-not $AsyncResult.AsyncWaitHandle.WaitOne(1000, $false)) {
            return $false
        }

        $Client.EndConnect($AsyncResult)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $Client.Close()
    }
}

function Get-TrackedProcess {
    param(
        [string]$PidFile,
        [string]$ExpectedModule
    )

    if (-not (Test-Path $PidFile)) {
        return $null
    }

    $PidContent = (Get-Content $PidFile -Raw).Trim()
    $ProcessId = 0

    if (-not [int]::TryParse($PidContent, [ref]$ProcessId)) {
        Write-Warning "Invalid PID file: $PidFile"
        Remove-Item $PidFile -Force
        return $null
    }

    try {
        $ProcessInfo = Get-CimInstance Win32_Process `
            -Filter "ProcessId = $ProcessId" `
            -ErrorAction Stop

        if (-not $ProcessInfo) {
            Remove-Item $PidFile -Force
            return $null
        }

        $ActualExecutable = [System.IO.Path]::GetFullPath(
            $ProcessInfo.ExecutablePath
        )

        $ExpectedExecutable = [System.IO.Path]::GetFullPath(
            $PythonPath
        )

        $ExpectedCommand = "-m $ExpectedModule"

        $IsExpectedProcess = (
            $ActualExecutable -ieq $ExpectedExecutable -and
            $ProcessInfo.CommandLine.IndexOf(
                $ExpectedCommand,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -ge 0
        )

        if (-not $IsExpectedProcess) {
            Write-Warning "PID $ProcessId does not match $ExpectedModule. PID file removed; process left untouched."
            Remove-Item $PidFile -Force
            return $null
        }

        return Get-Process -Id $ProcessId -ErrorAction Stop
    }
    catch {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }
}

function Wait-TcpPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutSeconds
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $Deadline) {
        if (Test-TcpPort -HostName $HostName -Port $Port) {
            return $true
        }

        Start-Sleep -Milliseconds 500
    }

    return $false
}

function Start-ManagedProcess {
    param(
        [string]$Module,
        [string]$PidFile,
        [string]$StdOutLog,
        [string]$StdErrLog
    )

    $Process = Start-Process `
        -FilePath $PythonPath `
        -ArgumentList @("-m", $Module) `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $StdOutLog `
        -RedirectStandardError $StdErrLog `
        -WindowStyle Hidden `
        -PassThru

    Set-Content -Path $PidFile -Value $Process.Id -Encoding ASCII

    return $Process
}

function Get-MosquittoStatus {
    try {
        $Service = Get-Service -Name "mosquitto" -ErrorAction Stop
        $PortAvailable = Test-TcpPort -HostName "127.0.0.1" -Port $MqttPort

        return @{
            Service = $Service.Status
            Port    = $PortAvailable
        }
    }
    catch {
        return @{
            Service = "Not found"
            Port    = $false
        }
    }
}

function Show-Status {
    $OpcUaProcess = Get-TrackedProcess $OpcUaPidFile $OpcUaModule
    $GatewayProcess = Get-TrackedProcess $GatewayPidFile $GatewayModule
    $Mqtt = Get-MosquittoStatus

    Write-Host "`nIndustrial Cloud Development Environment"
    Write-Host "----------------------------------------"

    Write-Host ("Mosquitto service : {0}" -f $Mqtt.Service)
    Write-Host ("MQTT port 1883    : {0}" -f $(if ($Mqtt.Port) { "Available" } else { "Unavailable" }))

    Write-Host ("OPC UA process    : {0}" -f $(if ($OpcUaProcess) { "Running (PID $($OpcUaProcess.Id))" } else { "Stopped" }))
    Write-Host ("OPC UA port 4840  : {0}" -f $(if (Test-TcpPort "127.0.0.1" $OpcUaPort) { "Available" } else { "Unavailable" }))

    Write-Host ("Gateway process   : {0}" -f $(if ($GatewayProcess) { "Running (PID $($GatewayProcess.Id))" } else { "Stopped" }))
    Write-Host ""
}

function Start-Environment {
    Initialize-Runtime

    if (-not (Test-Path $PythonPath)) {
        throw "Python virtual environment not found: $PythonPath"
    }

    if (Get-TrackedProcess $OpcUaPidFile $OpcUaModule) {
        throw "OPC UA server is already running."
    }

    if (Get-TrackedProcess $GatewayPidFile $GatewayModule) {
        throw "Gateway is already running."
    }

    if (Test-TcpPort "127.0.0.1" $OpcUaPort) {
        throw "OPC UA port 4840 is already occupied by an unmanaged process."
    }

    $Mqtt = Get-MosquittoStatus

    if ($Mqtt.Service -ne "Running" -or -not $Mqtt.Port) {
        throw "Mosquitto service or MQTT port 1883 is unavailable."
    }

    # Remove stale signals so a previous shutdown cannot stop new processes.
    Remove-Item $GatewayStopSignal, $OpcUaStopSignal `
        -Force -ErrorAction SilentlyContinue

    Write-Host "Starting OPC UA server..."

    $OpcUaProcess = Start-ManagedProcess `
        -Module $OpcUaModule `
        -PidFile $OpcUaPidFile `
        -StdOutLog $OpcUaLog `
        -StdErrLog "$OpcUaLog.err"

    if (-not (Wait-TcpPort "127.0.0.1" $OpcUaPort $StartupTimeoutSeconds)) {
        if (-not $OpcUaProcess.HasExited) {
            Stop-Process -Id $OpcUaProcess.Id -Force
        }

        Remove-Item $OpcUaPidFile -Force -ErrorAction SilentlyContinue
        throw "OPC UA server did not become ready. Check $OpcUaLog.err"
    }

    Write-Host "OPC UA server ready."
    Write-Host "Starting Industrial Gateway..."

    $GatewayProcess = Start-ManagedProcess `
        -Module $GatewayModule `
        -PidFile $GatewayPidFile `
        -StdOutLog $GatewayLog `
        -StdErrLog "$GatewayLog.err"

    Start-Sleep -Seconds 2

    if ($GatewayProcess.HasExited) {
        # Gateway startup failed, so only the OPC UA server needs to stop.
        New-Item -ItemType File -Path $OpcUaStopSignal -Force |
        Out-Null

        $Deadline = (Get-Date).AddSeconds($ShutdownTimeoutSeconds)

        while ((Get-Date) -lt $Deadline) {
            if (-not (Get-TrackedProcess $OpcUaPidFile $OpcUaModule)) {
                break
            }

            Start-Sleep -Milliseconds 500
        }

        $RemainingProcess = Get-TrackedProcess $OpcUaPidFile $OpcUaModule

        if ($RemainingProcess) {
            Write-Warning "OPC UA graceful shutdown timed out. Stopping PID $($RemainingProcess.Id)."
            Stop-Process -Id $RemainingProcess.Id -Force
        }

        Remove-Item $GatewayPidFile, $OpcUaPidFile `
            -Force -ErrorAction SilentlyContinue
        Remove-Item $GatewayStopSignal, $OpcUaStopSignal `
            -Force -ErrorAction SilentlyContinue

        throw "Gateway failed during startup. Check $GatewayLog.err"
    }

    Write-Host "Gateway process started."
    Show-Status
}

function Stop-Environment {
    Initialize-Runtime

    $OpcUaProcess = Get-TrackedProcess $OpcUaPidFile $OpcUaModule
    $GatewayProcess = Get-TrackedProcess $GatewayPidFile $GatewayModule

    if (-not $OpcUaProcess -and -not $GatewayProcess) {
        Remove-Item $GatewayStopSignal, $OpcUaStopSignal `
            -Force -ErrorAction SilentlyContinue
        Write-Host "No managed processes are running."
        return
    }

    # Stop Gateway first. It must close its OPC UA client session
    # while the OPC UA server is still available.
    if ($GatewayProcess) {
        New-Item -ItemType File -Path $GatewayStopSignal -Force |
        Out-Null

        Write-Host "Gateway shutdown signal created."

        $Deadline = (Get-Date).AddSeconds($ShutdownTimeoutSeconds)

        while ((Get-Date) -lt $Deadline) {
            $GatewayProcess = Get-TrackedProcess $GatewayPidFile $GatewayModule

            if (-not $GatewayProcess) {
                break
            }

            Start-Sleep -Milliseconds 500
        }

        $GatewayProcess = Get-TrackedProcess $GatewayPidFile $GatewayModule

        if ($GatewayProcess) {
            # Force termination is a fallback, not the normal shutdown path.
            Write-Warning "Gateway shutdown timeout. Stopping managed PID $($GatewayProcess.Id)."
            Stop-Process -Id $GatewayProcess.Id -Force
        }

        Remove-Item $GatewayPidFile -Force -ErrorAction SilentlyContinue
    }

    # Only request OPC UA shutdown after the Gateway process has exited.
    $OpcUaProcess = Get-TrackedProcess $OpcUaPidFile $OpcUaModule

    if ($OpcUaProcess) {
        New-Item -ItemType File -Path $OpcUaStopSignal -Force |
        Out-Null

        Write-Host "OPC UA shutdown signal created."

        $Deadline = (Get-Date).AddSeconds($ShutdownTimeoutSeconds)

        while ((Get-Date) -lt $Deadline) {
            $OpcUaProcess = Get-TrackedProcess $OpcUaPidFile $OpcUaModule

            if (-not $OpcUaProcess) {
                break
            }

            Start-Sleep -Milliseconds 500
        }

        $OpcUaProcess = Get-TrackedProcess $OpcUaPidFile $OpcUaModule

        if ($OpcUaProcess) {
            Write-Warning "OPC UA shutdown timeout. Stopping managed PID $($OpcUaProcess.Id)."
            Stop-Process -Id $OpcUaProcess.Id -Force
        }

        Remove-Item $OpcUaPidFile -Force -ErrorAction SilentlyContinue
    }

    # Remove both signals after the managed processes have stopped.
    Remove-Item $GatewayStopSignal, $OpcUaStopSignal `
        -Force -ErrorAction SilentlyContinue

    Write-Host "Managed processes stopped."
}

switch ($Action) {
    "start" { Start-Environment }
    "status" { Show-Status }
    "stop" { Stop-Environment }
}
