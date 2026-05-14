# fix_simple.py
import psycopg2

# Connexion directe
conn = psycopg2.connect(
    dbname="navette_db2_bspr_d0an",  # Notez le _d0an
    user="navette_db2_bspr_user", 
    password="yillROpVlewSMfY61F0Ae1w8FMyWhIPH",  # Mot de passe de render.yaml
    host="dpg-d82evchj2pic73afome0-a",  # Host interne
    port=5432
     connect_timeout=10
)

conn.autocommit = True
cur = conn.cursor()

# Corriger la séquence
cur.execute("SELECT setval('gestion_affectation_id_seq', COALESCE((SELECT MAX(id) FROM gestion_affectation), 1))")
print("✅ Séquence gestion_affectation corrigée !")

cur.close()
conn.close()