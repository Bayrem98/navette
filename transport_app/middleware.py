# middleware.py
from django.db import connection

class AutoFixSequencesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Correction au démarrage
        self.fix_sequences()
    
    def fix_sequences(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT setval('django_admin_log_id_seq', COALESCE((SELECT MAX(id) FROM django_admin_log), 1))")
                cursor.execute("SELECT setval('gestion_affectation_id_seq', COALESCE((SELECT MAX(id) FROM gestion_affectation), 1))")
                cursor.execute("SELECT setval('gestion_course_id_seq', COALESCE((SELECT MAX(id) FROM gestion_course), 1))")
                print("✅ Séquences corrigées automatiquement")
        except:
            pass

    def __call__(self, request):
        return self.get_response(request)