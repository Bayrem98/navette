# sauvegarde_direct.py
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Chemin COMPLET vers pg_dump (version 18)
pg_dump_path = r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"

# Vérifie si le fichier existe
if not os.path.exists(pg_dump_path):
    print(f"❌ pg_dump non trouvé")
    print(f"   Chemin recherché: {pg_dump_path}")
    print(f"   Vérifiez que PostgreSQL 18 est bien installé à cet endroit")
    exit(1)

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL non trouvée")
    print("   Créez un fichier .env avec: DATABASE_URL=postgresql://...")
    exit(1)

date_sauvegarde = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
nom_fichier = f"sauvegarde_{date_sauvegarde}.sql"

print(f"🔄 Sauvegarde en cours...")
print(f"📁 Fichier: {nom_fichier}")
print(f"🔧 Utilisation de: {pg_dump_path}")

# Exécute la commande
try:
    commande = f'"{pg_dump_path}" --no-owner "{DATABASE_URL}"'
    with open(nom_fichier, 'w', encoding='utf-8') as f:
        resultat = subprocess.run(commande, shell=True, stdout=f, stderr=subprocess.PIPE)
    
    if resultat.returncode == 0:
        taille = os.path.getsize(nom_fichier) / 1024
        print(f"✅ Sauvegarde réussie ! ({taille:.2f} KB)")
        print(f"💾 Fichier sauvegardé: {nom_fichier}")
    else:
        print(f"❌ Erreur: {resultat.stderr.decode()}")
except Exception as e:
    print(f"❌ Erreur: {e}")