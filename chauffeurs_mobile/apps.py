from django.apps import AppConfig

class ChauffeursMobileConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chauffeurs_mobile'
    verbose_name = 'Interface Mobile Chauffeurs'
    def has_admin_module(self):
        return False
