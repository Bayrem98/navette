from django.apps import AppConfig
import os
from django.conf import settings

class GestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion'
    
    def ready(self):
        """Charge le planning depuis Cloudinary au démarrage"""
        # Vérifier si le fichier existe dans la session (pour l'admin)
        # Cette fonction sera appelée après le démarrage de Django
        pass