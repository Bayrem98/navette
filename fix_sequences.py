# fix_sequences.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navette.settings')  # Remplacez par votre settings
django.setup()

from django.db import connection
from django.apps import apps

def fix_all_sequences():
    """Corrige toutes les séquences automatiquement"""
    with connection.cursor() as cursor:
        # Récupérer tous les modèles
        for model in apps.get_models():
            table_name = model._meta.db_table
            id_field = model._meta.pk
            
            if id_field and id_field.auto_created:
                try:
                    cursor.execute(f'SELECT COALESCE(MAX(id), 0) FROM "{table_name}"')
                    max_id = cursor.fetchone()[0]
                    
                    sequence_name = f"{table_name}_id_seq"
                    cursor.execute(f'SELECT setval(\'{sequence_name}\', {max_id})')
                    
                    if max_id > 0:
                        print(f"✅ {table_name}: séquence réinitialisée à {max_id}")
                except Exception as e:
                    print(f"⚠️ {table_name}: {e}")
        
        print("\n🎉 Correction terminée !")

if __name__ == "__main__":
    fix_all_sequences()