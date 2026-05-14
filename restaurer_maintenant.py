# restaurer_maintenant_corrige.py
import subprocess
import os
import re

print("=" * 50)
print("🔄 RESTAURATION DE LA BASE RENDER")
print("=" * 50)
print()

# 1. Demander la nouvelle URL
print("📎 Allez sur votre dashboard Render et copiez la Connection String")
print("   (l'URL complète qui commence par postgresql://)")
print()
url_entree = input("Collez l'URL ici: ").strip()

# 2. Corriger l'URL si besoin (ajouter domaine et port)
def corriger_url(url):
    # Si le port 5432 est manquant, l'ajouter
    if ":5432" not in url:
        # Trouver la position après @ et avant le prochain /
        match = re.search(r'@([^/:]+)(?:/|$)', url)
        if match:
            host = match.group(1)
            # Si le host ne contient pas .render.com, l'ajouter
            if ".render.com" not in host:
                host_corrige = host + ".oregon-postgres.render.com"
                url = url.replace(host, host_corrige)
            # Ajouter le port :5432
            url = url.replace(host_corrige, host_corrige + ":5432")
    return url

nouvelle_url = corriger_url(url_entree)
print(f"\n✅ URL corrigée: {nouvelle_url[:80]}...")

# 3. Lister les sauvegardes disponibles
print("\n📁 Vos fichiers de sauvegarde :")
fichiers = [f for f in os.listdir('.') if f.startswith('sauvegarde_') and f.endswith('.sql') and os.path.getsize(f) > 0]

if not fichiers:
    print("   Aucun fichier de sauvegarde trouvé !")
    exit(1)

for i, f in enumerate(fichiers, 1):
    taille = os.path.getsize(f) / 1024
    print(f"   {i}. {f} ({taille:.2f} KB)")

# 4. Demander quel fichier restaurer
print()
nom_fichier = input("📂 Nom du fichier à restaurer (ex: sauvegarde_2026-04-14_00-59.sql): ").strip()

if not os.path.exists(nom_fichier):
    print(f"❌ Fichier {nom_fichier} non trouvé")
    exit(1)

# 5. Confirmation
print()
print(f"⚠️  Attention : Cela va REMPLACER toutes les données dans la nouvelle base")
reponse = input("Êtes-vous sûr de vouloir continuer ? (oui/non): ").strip().lower()

if reponse != "oui":
    print("❌ Annulé")
    exit(1)

# 6. Restauration
psql_path = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"

print()
print("🔄 Restauration en cours...")
print(f"   Fichier: {nom_fichier}")
print()

try:
    # Utiliser la commande avec redirection
    commande = f'"{psql_path}" "{nouvelle_url}"'
    with open(nom_fichier, 'r', encoding='utf-8') as f:
        resultat = subprocess.run(commande, shell=True, stdin=f, capture_output=True, text=True)
    
    if resultat.returncode == 0:
        print("=" * 50)
        print("✅ RESTAURATION REUSSIE !")
        print("=" * 50)
        print("Vos données ont été restaurées avec succès.")
    else:
        print("=" * 50)
        print("❌ ERREUR LORS DE LA RESTAURATION")
        print("=" * 50)
        print(resultat.stderr[:500])
        
        if "password" in resultat.stderr.lower():
            print("\n💡 Le mot de passe semble incorrect")
        elif "does not exist" in resultat.stderr.lower():
            print("\n💡 La base de données n'existe pas")
        elif "translate host name" in resultat.stderr.lower():
            print("\n💡 Le nom d'hôte est incorrect")
            print(f"   Vérifiez que l'URL contient bien: .oregon-postgres.render.com:5432")

except Exception as e:
    print(f"❌ Erreur: {e}")

print()
input("Appuyez sur Entrée pour fermer...")