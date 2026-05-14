# sauvegarde_auto.py
import subprocess
import os
from datetime import datetime
import shutil

print("=" * 50)
print("🔄 SAUVEGARDE AUTOMATIQUE")
print("=" * 50)
print()

# 1. Sauvegarde de la base
print("1️⃣ Sauvegarde de la base de données...")
resultat = subprocess.run([".\\sauvegarde.bat"], shell=True)

if resultat.returncode != 0:
    print("❌ Échec de la sauvegarde !")
    exit(1)

# 2. Trouver le dernier fichier de sauvegarde
fichiers = [f for f in os.listdir('.') if f.startswith('sauvegarde_') and f.endswith('.sql')]
if fichiers:
    dernier = max(fichiers, key=os.path.getctime)
    taille = os.path.getsize(dernier) / 1024
    print(f"\n2️⃣ Dernière sauvegarde: {dernier} ({taille:.2f} KB)")
else:
    print("❌ Aucun fichier de sauvegarde trouvé")
    exit(1)

# 3. Copie vers un dossier de backup local
dossier_backup = "C:\\Users\\Bayrem\\Desktop\\sauvegardes_navette"
if not os.path.exists(dossier_backup):
    os.makedirs(dossier_backup)

shutil.copy(dernier, dossier_backup)
print(f"3️⃣ Copie locale: {dossier_backup}\\{dernier}")

# 4. Afficher le résumé
print("\n" + "=" * 50)
print("✅ SAUVEGARDE TERMINÉE")
print("=" * 50)
print(f"📁 Fichier: {dernier}")
print(f"💾 Taille: {taille:.2f} KB")
print(f"📂 Dossier: {dossier_backup}")
print("\n💡 N'oubliez pas de copier ce fichier sur Google Drive !")