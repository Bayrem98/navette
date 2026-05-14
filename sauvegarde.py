# sauvegarde.py
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Charge votre URL de base de données depuis .env (ou Render)
load_dotenv()

# Récupère l'URL de votre base de données (Render, Railway, etc.)
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ Erreur: DATABASE_URL non trouvée dans les variables d'environnement")
    exit(1)

# Crée un nom de fichier avec la date et l'heure
date_sauvegarde = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
nom_fichier = f"sauvegarde_{date_sauvegarde}.sql"

print(f"🔄 Sauvegarde en cours...")
print(f"📁 Fichier: {nom_fichier}")

# Exécute la commande pg_dump
commande = f"pg_dump --no-owner '{DATABASE_URL}' > {nom_fichier}"
resultat = subprocess.run(commande, shell=True)

if resultat.returncode == 0:
    taille = os.path.getsize(nom_fichier) / 1024  # Taille en KB
    print(f"✅ Sauvegarde réussie ! ({taille:.2f} KB)")
    print(f"💾 Fichier sauvegardé: {nom_fichier}")
else:
    print("❌ Erreur lors de la sauvegarde")