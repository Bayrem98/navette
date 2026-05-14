from django.apps import AppConfig
import os
from django.conf import settings

class GestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion'
    
    def ready(self):
        """Charge le planning au démarrage si un fichier existe"""
        import os
        from django.conf import settings
        from .utils import GestionnaireTransport
        
        # Créer un faux request pour charger le planning
        class FakeRequest:
            def __init__(self):
                self.session = {}
                self.user = None
            
            def get(self, key, default=None):
                return self.session.get(key, default)
        
        fake_request = FakeRequest()
        
        # Vérifier si un fichier planning existe dans media
        temp_path = os.path.join(settings.MEDIA_ROOT, 'temp_planning.xlsx')
        if os.path.exists(temp_path):
            print(f"🔄 Chargement automatique du planning depuis {temp_path}")
            gestionnaire = GestionnaireTransport(request=fake_request)
            if gestionnaire.charger_planning(temp_path):
                print("✅ Planning chargé automatiquement au démarrage")
                # Stocker les infos dans la session factice
                fake_request.session['planning_charge'] = True
                fake_request.session['gestionnaire_dates'] = gestionnaire.dates_par_jour