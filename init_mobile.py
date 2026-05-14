#!/usr/bin/env python
"""
Script d'initialisation de l'interface mobile
VERSION SIMPLIFIÉE - Crée seulement des chauffeurs de test si nécessaire
"""

import os
import sys
import django
import hashlib

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_app.settings')

try:
    django.setup()
    
    from gestion.models import Chauffeur
    
    def init_mobile_data():
        """Initialiser les données pour l'interface mobile"""
        
        print("🚀 Initialisation des données mobile...")
        
        # Vérifier s'il y a déjà des chauffeurs
        chauffeurs_existants = Chauffeur.objects.count()
        print(f"📊 {chauffeurs_existants} chauffeur(s) existant(s)")
        
        # Si pas de chauffeurs, en créer un de test
        if chauffeurs_existants == 0:
            print("📝 Création d'un chauffeur de test...")
            
            chauffeur_test = {
                'nom': 'Chauffeur Test',
                'telephone': '12345678',
                'type_chauffeur': 'taxi',
                'numero_voiture': 'TEST1234',
                'actif': True
            }
            
            chauffeur, created = Chauffeur.objects.get_or_create(
                telephone=chauffeur_test['telephone'],
                defaults=chauffeur_test
            )
            
            # Définir le mot de passe mobile
            if created:
                pin_hash = hashlib.sha256('1234'.encode()).hexdigest()
                chauffeur.mobile_password = pin_hash
                chauffeur.save()
                print(f"✅ Chauffeur de test créé: {chauffeur.nom}")
            else:
                print(f"🔧 Chauffeur mis à jour: {chauffeur.nom}")
        else:
            print("✅ Des chauffeurs existent déjà - pas de création nécessaire")
        
        print("\n" + "="*60)
        print("🎉 INITIALISATION TERMINÉE !")
        print("="*60)
        print("\n📱 POUR TESTER :")
        print("   1. Créez un chauffeur dans l'admin Django")
        print("   2. Définissez son mot de passe mobile (ex: 1234)")
        print("   3. Connectez-vous sur: http://localhost:8000/mobile/login/")
        print("="*60)
    
    if __name__ == '__main__':
        init_mobile_data()

except Exception as e:
    print(f"❌ Erreur lors de l'initialisation: {e}")
    print("⚠️  Assurez-vous que Django est correctement configuré")
