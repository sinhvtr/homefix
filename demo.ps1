# HomeFix — chạy bản DEMO qua Cloudflare Quick Tunnel, không cần Claude (docs/HUONG_DAN_DEMO.md).
# Cách dùng (nhấp đúp demo.bat, hoặc trong PowerShell tại thư mục dự án):
#   .\demo.bat            bật Docker Desktop (nếu tắt) → chạy bản demo → in địa chỉ https://….trycloudflare.com
#   .\demo.bat tat        tắt tunnel (địa chỉ hết hiệu lực ngay; dữ liệu giữ nguyên)
#   .\demo.bat dev        tắt tunnel và quay về cấu hình dev (runserver) để lập trình tiếp
#   .\demo.bat diachi     in lại địa chỉ hiện tại
param([string]$Lenh = "bat")

# "Continue": PowerShell 5.1 coi dòng stderr của docker (tiến trình, nhật ký) là lỗi nếu để "Stop"
$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$DEMO = @("compose", "-f", "docker-compose.yml", "-f", "docker-compose.demo.yml")

function Viet($chu, $mau = "Gray") { Write-Host $chu -ForegroundColor $mau }

function DockerChay {
    # "docker info" trả lời trước khi engine sẵn sàng hẳn → kiểm thêm việc đọc danh sách image, container
    cmd /c "docker info --format {{.ServerVersion}} >nul 2>&1 && docker image ls -q >nul 2>&1 && docker ps -q >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
}

function ChoDocker([int]$giay) {
    for ($i = 0; $i -lt $giay; $i += 3) {
        if (DockerChay) { return $true }
        Start-Sleep -Seconds 3
    }
    return $false
}

function BatDocker {
    if (DockerChay) { return }
    $exe = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $exe)) { throw "Không thấy Docker Desktop ở $exe — hãy cài Docker Desktop." }
    Viet "Đang bật Docker Desktop (lần đầu có thể mất 1–2 phút)…" Yellow
    Start-Process $exe
    if (ChoDocker 150) { return }
    # Lỗi đã gặp: socket cũ trong %LOCALAPPDATA%\Docker\run làm Docker Desktop không khởi động được.
    Viet "Docker chưa lên — thử dọn thư mục socket cũ rồi bật lại…" Yellow
    Get-Process "Docker Desktop", "com.docker.backend" -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 3
    $run = Join-Path $env:LOCALAPPDATA "Docker\run"
    if (Test-Path $run) { Rename-Item $run ("run.cu-" + (Get-Date -Format "yyyyMMddHHmmss")) }
    Start-Process $exe
    if (-not (ChoDocker 180)) { throw "Docker Desktop vẫn chưa chạy. Mở Docker Desktop bằng tay, đợi biểu tượng cá voi đứng yên rồi chạy lại demo.bat." }
}

function LayDiaChi {
    $nhat_ky = cmd /c "docker compose -f docker-compose.yml -f docker-compose.demo.yml logs tunnel 2>&1" | Out-String
    $ds = [regex]::Matches($nhat_ky, "https://[a-z0-9-]+\.trycloudflare\.com")
    if ($ds.Count -gt 0) { return $ds[$ds.Count - 1].Value }
    return $null
}

switch ($Lenh) {
    "tat" {
        BatDocker
        & docker @DEMO stop tunnel; & docker @DEMO rm -f tunnel
        Viet "Đã tắt tunnel — địa chỉ cũ hết hiệu lực." Green
    }
    "dev" {
        BatDocker
        & docker @DEMO stop tunnel; & docker @DEMO rm -f tunnel
        & docker compose up -d --build
        Viet "Đã về cấu hình dev: http://localhost:8000" Green
    }
    "diachi" {
        $u = LayDiaChi
        if ($u) { Viet $u Cyan } else { Viet "Chưa có tunnel — chạy: .\demo.bat" Yellow }
    }
    default {
        BatDocker
        Viet "Đang chạy bản demo (build lần đầu có thể mất vài phút)…" Yellow
        for ($lan = 1; $lan -le 3; $lan++) {
            & docker @DEMO up -d --build --wait db web
            if ($LASTEXITCODE -eq 0) { break }
            if ($lan -eq 3) { throw "Không chạy được web — xem: docker compose logs web" }
            Viet "Docker chưa sẵn sàng, thử lại sau 15 giây…" Yellow
            Start-Sleep -Seconds 15
        }
        & docker @DEMO up -d worker backup
        # Tạo lại container tunnel để lấy địa chỉ mới, tránh đọc nhầm địa chỉ cũ trong nhật ký
        & docker @DEMO up -d --force-recreate tunnel
        $u = $null
        for ($i = 0; $i -lt 30 -and -not $u; $i++) { Start-Sleep -Seconds 2; $u = LayDiaChi }
        if (-not $u) { throw "Tunnel chưa cấp địa chỉ — kiểm tra mạng rồi chạy lại; xem: docker compose -f docker-compose.yml -f docker-compose.demo.yml logs tunnel" }
        $ok = $false
        for ($i = 0; $i -lt 15 -and -not $ok; $i++) {
            try { $ok = (Invoke-WebRequest "$u/suc-khoe/" -UseBasicParsing -TimeoutSec 10).StatusCode -eq 200 } catch { Start-Sleep -Seconds 2 }
        }
        $da_chep = $true
        try { Set-Clipboard -Value $u } catch { $da_chep = $false }
        Viet ""
        if ($da_chep) { Viet "  Địa chỉ demo (đã chép vào clipboard):" Green } else { Viet "  Địa chỉ demo:" Green }
        Viet "  $u" Cyan
        if (-not $ok) { Viet "  (địa chỉ có thể cần thêm vài giây mới mở được)" Yellow }
        Viet ""
        Viet "  Tắt tunnel: .\demo.bat tat     Về cấu hình dev: .\demo.bat dev" Gray
    }
}
