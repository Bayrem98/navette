# restaurer_simple.py
from multiprocessing.dummy import connection
import subprocess
import sys

# Votre URL Render (CORRECTE avec domaine et port)
URL = "postgresql://navette_db2_bspr_user:KUSOSoMwHvIPMAovfmpIMycmfmY3IrER@dpg-d7f6srreo5us73eed1hg-a.oregon-postgres.render.com/navette_db2_bspr_gwyw"

# Votre fichier de sauvegarde
FICHIER = "sauvegarde_2026-04-16_23-39.sql"

print("🔄 Restauration en cours...")
print(f"   Fichier: {FICHIER}")
print(f"   Destination: Render PostgreSQL")
print()

try:
    # Lire le fichier et l'envoyer à psql
    with open(FICHIER, 'r', encoding='utf-8') as f:
        contenu = f.read()
    
    # Exécuter psql avec le contenu
    processus = subprocess.run(
        [r"C:\Program Files\PostgreSQL\18\bin\psql.exe", URL],
        input=contenu,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    if processus.returncode == 0:
        print("=" * 50)
        print("✅ RESTAURATION REUSSIE !")
        print("=" * 50)
        
        # Vérification rapide
        verif = subprocess.run(
            [r"C:\Program Files\PostgreSQL\18\bin\psql.exe", URL, "-c", "SELECT COUNT(*) FROM auth_user;"],
            capture_output=True,
            text=True
        )
        if verif.returncode == 0:
            print("\n📊 Vérification:")
            print(verif.stdout)
    else:
        print("=" * 50)
        print("❌ ERREUR LORS DE LA RESTAURATION")
        print("=" * 50)
        print(processus.stderr[:500])
        
except FileNotFoundError:
    print("❌ Fichier de sauvegarde non trouvé")
    print(f"   Vérifiez que {FICHIER} existe dans le dossier")
except Exception as e:
    print(f"❌ Erreur: {e}")

input("\nAppuyez sur Entrée pour fermer...")

# Après la restauration, ajoutez :
print("🔄 Correction des séquences...")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT 'SELECT setval(''' || seq.relname || ''', COALESCE(MAX(id), 1)) FROM ' || tab.relname || ';'
        FROM pg_class seq
        JOIN pg_depend d ON d.objid = seq.oid
        JOIN pg_class tab ON d.refobjid = tab.oid
        WHERE seq.relkind = 'S' AND d.deptype = 'a'
    """)
print("✅ Séquences corrigées")