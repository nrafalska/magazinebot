# ============================================
# РОЗДІЛЕННЯ ЧЕРЕЗ SCRIPTS PANEL
# ============================================

$templatesRoot = "C:\Projects\magazinebot\data\templates"
$backupDir = "C:\Projects\magazinebot\data\templates\_ORIGINALS_BACKUP"
$scriptsDir = "C:\Projects\magazinebot\scripts"
$indesignScriptPath = "C:\Users\ashie\AppData\Roaming\Adobe\InDesign\Version 21.0\uk_UA\Scripts\Scripts Panel\SplitAllTemplates.jsx"

if (-not (Test-Path $backupDir)) {
    New-Item -Path $backupDir -ItemType Directory -Force | Out-Null
}

$logFile = "C:\Projects\magazinebot\split_templates_log.txt"
"=== Початок: $(Get-Date) ===" | Out-File $logFile

# Знайти всі файли
$templateFiles = Get-ChildItem -Path $templatesRoot -Filter "*.indd" -Recurse -File

Write-Host "Знайдено $($templateFiles.Count) шаблонів`n" -ForegroundColor Cyan

# Підготувати параметри для InDesign
$params = @{
    files = @()
    outputDir = ""
    backupDir = $backupDir.Replace('\', '/')
}

foreach ($file in $templateFiles) {
    $params.files += @{
        path = $file.FullName.Replace('\', '/')
        name = $file.Name
    }
}

$paramsJson = $params | ConvertTo-Json -Depth 10
$paramsJson | Out-File "$scriptsDir\split_params.json" -Encoding UTF8

Write-Host "Параметри збережено" -ForegroundColor Gray
Write-Host "Запуск InDesign зі скриптом...`n" -ForegroundColor Yellow

# Видалити старий результат
$resultFile = "$scriptsDir\split_results.json"
if (Test-Path $resultFile) {
    Remove-Item $resultFile -Force
}

# Запустити InDesign зі скриптом
try {
    $indesignExe = "C:\Program Files\Adobe\Adobe InDesign 2026\InDesign.exe"
    $process = Start-Process -FilePath $indesignExe -ArgumentList "`"$indesignScriptPath`"" -PassThru
    
    Write-Host "InDesign запущено. Чекаємо завершення..." -ForegroundColor Gray
    
    # Чекати результату (max 10 хвилин)
    $timeout = 600
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        if (Test-Path $resultFile) {
            Write-Host "`n✅ Результати отримано!" -ForegroundColor Green
            break
        }
        Start-Sleep -Seconds 2
        $elapsed += 2
        if ($elapsed % 20 -eq 0) {
            Write-Host "  Обробка... $elapsed сек" -ForegroundColor DarkGray
        }
    }
    
    if (Test-Path $resultFile) {
        $results = Get-Content $resultFile -Raw | ConvertFrom-Json
        
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "РЕЗУЛЬТАТИ:" -ForegroundColor White
        Write-Host "========================================`n" -ForegroundColor Cyan
        
        $successCount = 0
        $errorCount = 0
        
        foreach ($result in $results) {
            if ($result.status -eq "SUCCESS") {
                Write-Host "✅ $($result.file) → $($result.created) файлів" -ForegroundColor Green
                $successCount++
                
                # Перемістити оригінал в backup
                $originalPath = $templateFiles | Where-Object {$_.Name -eq $result.file} | Select-Object -First 1
                if ($originalPath) {
                    $backupPath = Join-Path $backupDir "$($originalPath.BaseName)_ORIGINAL.indd"
                    Move-Item -Path $originalPath.FullName -Destination $backupPath -Force -ErrorAction SilentlyContinue
                    Write-Host "   📦 Backup збережено" -ForegroundColor Cyan
                }
                
            } else {
                Write-Host "❌ $($result.file) → $($result.message)" -ForegroundColor Red
                $errorCount++
            }
        }
        
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "Успішно: $successCount | Помилки: $errorCount" -ForegroundColor White
        Write-Host "========================================" -ForegroundColor Cyan
        
    } else {
        Write-Host "⚠️ Timeout! Результати не отримано" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "❌ Помилка: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎉 Завершено!" -ForegroundColor Green
"=== Завершено: $(Get-Date) ===" | Out-File $logFile -Append
