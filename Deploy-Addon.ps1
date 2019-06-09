 $blenderversion = "2.80"
 $blenderaddondir = "$env:APPDATA\Blender Foundation\Blender\$blenderversion\scripts\addons"
 $sourcedir = "$env:HOME\source\repos\Cryengine Importer"

 
 write-host $blenderaddondir
 Write-Host $sourcedir

 Set-Location $sourcedir

 # Remove existing zip file
 # Create a new zip file from the io_cryengine_importer directory
 # Copy the contents of the zip file to the Blender addon directory.

 if (Test-Path "$sourcedir\io_cryengine_importer.zip") {
    Write-Host "Removing existing io_cryengine_importer.zip file." -ForegroundColor Green
    Remove-Item "$sourcedir\io_cryengine_importer.zip"
 }


 Compress-Archive "$sourcedir\io_cryengine_importer" -DestinationPath "$sourcedir\io_cryengine_importer.zip"
 Write-Host "Created new io_cryengine_importer.zip file to $sourcedir." -ForegroundColor Green

 # Copy to the Blender add-on folder and overwrite existing files

 Expand-Archive -Force "$sourcedir\io_cryengine_importer.zip" -DestinationPath "$blenderaddondir"
 Write-Host "Extracted zip file to Blender addon directory at $blenderaddondir" -ForegroundColor Green
