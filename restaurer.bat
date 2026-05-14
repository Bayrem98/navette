@echo off
echo RESTAURATION DE LA BASE DE DONNEES
echo.

set "URL=postgresql://navette_db2_bspr_user:yillROpVlewSMfY61F0Ae1w8FMyWhIPH@dpg-d82evchj2pic73afome0-a.oregon-postgres.render.com/navette_db2_bspr_d0an"
set "FICHIER=sauvegarde_2026-05-13_23-37.sql"

echo Restauration de %FICHIER% vers Render...
type "%FICHIER%" | "C:\Program Files\PostgreSQL\18\bin\psql.exe" "%URL%"

if %errorlevel%==0 (
    echo.
    echo ✅ RESTAURATION REUSSIE !
) else (
    echo.
    echo ❌ ERREUR lors de la restauration
)

pause