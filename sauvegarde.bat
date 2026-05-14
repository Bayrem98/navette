@echo off
echo 🔄 Sauvegarde de la base de donnees Render...

set "DATABASE_URL=postgresql://navette_db2_bspr_user:KUSOSoMwHvIPMAovfmpIMycmfmY3IrER@dpg-d7f6srreo5us73eed1hg-a.oregon-postgres.render.com/navette_db2_bspr_gwyw"

set NOM_FICHIER=sauvegarde_%date:~-4,4%-%date:~-7,2%-%date:~-10,2%_%time:~0,2%-%time:~3,2%.sql
set NOM_FICHIER=%NOM_FICHIER: =0%

echo Connexion a Render...
"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" --no-owner "%DATABASE_URL%" > "%NOM_FICHIER%"

if %errorlevel%==0 (
    echo ✅ Sauvegarde reussie : %NOM_FICHIER%
    echo 📁 Fichier cree dans: %CD%\%NOM_FICHIER%
) else (
    echo ❌ Erreur lors de la sauvegarde
)