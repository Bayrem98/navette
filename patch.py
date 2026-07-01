# patch.py
import sys
import django.template.context

if sys.version_info >= (3, 14):
    print("✅ Application du patch pour Python 3.14...")
    
    # Sauvegarder l'original
    original_copy = django.template.context.Context.__copy__
    
    def patched_copy(self):
        """Version corrigée pour Python 3.14"""
        duplicate = object.__new__(type(self))
        duplicate.dicts = self.dicts[:]
        # Copier tous les attributs qui existent
        for attr in dir(self):
            if not attr.startswith('_') and attr not in ['dicts']:
                try:
                    setattr(duplicate, attr, getattr(self, attr))
                except:
                    pass
        return duplicate
    
    # Appliquer le patch
    django.template.context.Context.__copy__ = patched_copy
    print("✅ Patch appliqué avec succès")