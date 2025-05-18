# Improved deploy script for Cryengine Importer Blender addon
[CmdletBinding()]
param (
    [string]$BlenderVersion = "4.0",
    [string]$SourceDir = "$env:HOME\source\repos\Cryengine Importer",
    [switch]$Force = $false
)

# Calculate paths
$BlenderAddonDir = "$env:APPDATA\Blender Foundation\Blender\$BlenderVersion\scripts\addons"
$ZipFile = "$SourceDir\io_cryengine_importer.zip"

Write-Host "===== Cryengine Importer Deployment =====" -ForegroundColor Cyan
Write-Host "Blender version: $BlenderVersion" -ForegroundColor Cyan
Write-Host "Addon directory: $BlenderAddonDir" -ForegroundColor Cyan
Write-Host "Source directory: $SourceDir" -ForegroundColor Cyan

# Verify paths exist
if (-not (Test-Path $SourceDir)) {
    Write-Host "Error: Source directory not found: $SourceDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "$SourceDir\io_cryengine_importer")) {
    Write-Host "Error: io_cryengine_importer directory not found in source directory" -ForegroundColor Red
    exit 1
}

# Remove old zip file if it exists
if (Test-Path $ZipFile) {
    Write-Host "Removing existing zip file..." -ForegroundColor Yellow
    Remove-Item $ZipFile -Force
}

# Check if the Blender version directory exists
$BlenderVersionDir = "$env:APPDATA\Blender Foundation\Blender\$BlenderVersion"
if (-not (Test-Path $BlenderVersionDir)) {
    if (-not $Force) {
        Write-Host "Error: Blender version $BlenderVersion does not appear to be installed." -ForegroundColor Red
        Write-Host "The directory does not exist: $BlenderVersionDir" -ForegroundColor Red
        Write-Host "If you want to deploy anyway, run the script with the -Force parameter:" -ForegroundColor Yellow
        Write-Host ".\Deploy-Addon.ps1 -BlenderVersion $BlenderVersion -Force" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Warning: Deploying to a non-existent Blender version because -Force was specified." -ForegroundColor Yellow
    Write-Host "Target directory does not exist: $BlenderVersionDir" -ForegroundColor Yellow
}

# Create Blender addon directory if it doesn't exist
if (-not (Test-Path $BlenderAddonDir)) {
    Write-Host "Creating Blender addon directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $BlenderAddonDir -Force | Out-Null
}

# Create zip file
try {
    Write-Host "Creating new zip file..." -ForegroundColor Yellow
    Compress-Archive -Path "$SourceDir\io_cryengine_importer" -DestinationPath $ZipFile -Force
    Write-Host "Zip file created successfully" -ForegroundColor Green
} catch {
    Write-Host "Error creating zip file: $_" -ForegroundColor Red
    exit 1
}

# Extract to Blender addon directory
try {
    Write-Host "Extracting to Blender addon directory..." -ForegroundColor Yellow
    Expand-Archive -Path $ZipFile -DestinationPath $BlenderAddonDir -Force
    Write-Host "Addon deployed successfully!" -ForegroundColor Green
} catch {
    Write-Host "Error extracting zip file: $_" -ForegroundColor Red
    exit 1
}

Write-Host "===== Deployment Complete =====" -ForegroundColor Cyan
Write-Host "Please restart Blender to see the changes" -ForegroundColor Cyan
