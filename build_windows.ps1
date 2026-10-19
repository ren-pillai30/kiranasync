# Windows Build & Packaging Script for KiranaSync 2.0
$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Building KiranaSync 2.0 Desktop Release" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Build frontend bundle
Write-Host "`n[1/3] Building frontend production bundle..." -ForegroundColor Yellow
Set-Location -Path "frontend"
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Frontend build failed!"
    exit 1
}
Set-Location -Path ".."

# 2. Verify backend test suite
Write-Host "`n[2/3] Verifying backend test suite..." -ForegroundColor Yellow
python -m unittest discover -s backend/tests -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backend tests failed! Halting build."
    exit 1
}

# 3. Package with PyInstaller
Write-Host "`n[3/3] Packaging executable via PyInstaller..." -ForegroundColor Yellow
pip install pyinstaller --quiet

pyinstaller --noconfirm --onedir --windowed `
    --name "KiranaSync" `
    --add-data "frontend/dist;frontend/dist" `
    --add-data "catalog.json;." `
    --hidden-import "clr_loader" `
    --hidden-import "pythonnet" `
    --hidden-import "number_parser" `
    --hidden-import "flask" `
    --hidden-import "flask_cors" `
    --hidden-import "requests" `
    overlay.py

Write-Host "`n=========================================" -ForegroundColor Green
Write-Host " Build Complete! Artifacts in dist/KiranaSync/" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
