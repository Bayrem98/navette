# planning_db.py - Version corrigée

import pandas as pd
from io import BytesIO
from datetime import datetime
from django.core.files.uploadedfile import UploadedFile
import os
import json
import re

class PlanningDB:
    """Gestionnaire de planning avec stockage en base de données"""
    
    @staticmethod
    def save_planning(file, nom_fichier=None):
        """
        Sauvegarde un planning Excel dans la base de données
        """
        try:
            from gestion.models import PlanningExcel
            
            # Lire le contenu du fichier
            if hasattr(file, 'read'):
                file.seek(0)  # Revenir au début
                content = file.read()
            elif isinstance(file, str) and os.path.exists(file):
                with open(file, 'rb') as f:
                    content = f.read()
            else:
                raise ValueError("Format de fichier non supporté")
            
            # Lire le fichier avec header=None pour avoir toutes les lignes
            df_raw = pd.read_excel(BytesIO(content), header=None, engine='openpyxl')
            
            print(f"📊 Fichier lu: {len(df_raw)} lignes, {len(df_raw.columns)} colonnes")
            
            # Trouver la ligne des en-têtes
            header_row_idx = None
            for idx in range(min(5, len(df_raw))):
                row = df_raw.iloc[idx]
                for cell in row:
                    if pd.notna(cell) and isinstance(cell, str):
                        if 'salarié' in str(cell).lower() or 'salarie' in str(cell).lower():
                            header_row_idx = idx
                            break
                if header_row_idx is not None:
                    break
            
            if header_row_idx is None:
                for idx in range(min(10, len(df_raw))):
                    row = df_raw.iloc[idx]
                    date_count = 0
                    for cell in row:
                        if pd.notna(cell) and isinstance(cell, str):
                            if re.search(r'\d{1,2}[/\-]\d{1,2}', str(cell)):
                                date_count += 1
                    if date_count >= 3:
                        header_row_idx = idx
                        break
            
            # Extraire les données
            if header_row_idx is not None:
                df = pd.read_excel(BytesIO(content), skiprows=header_row_idx + 1, engine='openpyxl')
                noms_colonnes = ['Salarie', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche', 'Qualification']
                if len(df.columns) > len(noms_colonnes):
                    df = df.iloc[:, :len(noms_colonnes)]
                elif len(df.columns) < len(noms_colonnes):
                    noms_colonnes = noms_colonnes[:len(df.columns)]
                df.columns = noms_colonnes
            else:
                # Fallback
                df = pd.read_excel(BytesIO(content), engine='openpyxl')
                for col in df.columns:
                    if 'salarié' in str(col).lower() or 'salarie' in str(col).lower():
                        df = df.rename(columns={col: 'Salarie'})
            
            # Nettoyer
            df = df.dropna(how='all').reset_index(drop=True)
            
            # Extraire les dates
            dates_disponibles = []
            if header_row_idx is not None:
                header_row = df_raw.iloc[header_row_idx]
                jours_ordre = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
                for i, jour in enumerate(jours_ordre):
                    col_idx = i + 1
                    if col_idx < len(header_row) and pd.notna(header_row[col_idx]):
                        cell_str = str(header_row[col_idx])
                        date_match = re.search(r'(\d{1,2}[/\-]\d{1,2})', cell_str)
                        if date_match:
                            try:
                                date_str = date_match.group(1)
                                date_obj = datetime.strptime(f"{date_str}/2026", "%d/%m/%Y")
                                dates_disponibles.append(date_obj.strftime('%Y-%m-%d'))
                            except:
                                try:
                                    date_obj = datetime.strptime(f"{date_str}/{datetime.now().year}", "%d/%m/%Y")
                                    dates_disponibles.append(date_obj.strftime('%Y-%m-%d'))
                                except:
                                    pass
            
            # Sauvegarder en base
            donnees_json = json.dumps(df.to_dict('records'))
            dates_json = json.dumps(dates_disponibles)
            
            planning = PlanningExcel.objects.create(
                nom_fichier=nom_fichier or 'planning.xlsx',
                donnees=donnees_json,
                dates_disponibles=dates_json,
                nombre_lignes=len(df),
                est_actif=True
            )
            
            PlanningExcel.objects.exclude(id=planning.id).update(est_actif=False)
            
            print(f"✅ Planning sauvegardé en base: {len(df)} lignes")
            print(f"📊 Colonnes: {list(df.columns)}")
            print(f"📅 Dates: {dates_disponibles}")
            return planning
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde planning: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_active_planning():
        try:
            from gestion.models import PlanningExcel
            return PlanningExcel.objects.filter(est_actif=True).first()
        except:
            return None
    
    @staticmethod
    def get_planning_as_dataframe():
        planning = PlanningDB.get_active_planning()
        if planning and planning.donnees:
            try:
                data = json.loads(planning.donnees)
                return pd.DataFrame(data)
            except:
                return None
        return None
    
    @staticmethod
    def get_planning_for_date(date_str):
        from gestion.models import PlanningExcel
        import json
        
        planning = PlanningExcel.objects.filter(est_actif=True).first()
        if not planning or not planning.donnees:
            print(f"⚠️ Aucun planning actif trouvé")
            return None
        
        try:
            data = json.loads(planning.donnees)
            df = pd.DataFrame(data)
            
            if 'date' in df.columns:
                filtered = df[df['date'] == date_str]
                if not filtered.empty:
                    return filtered.to_dict('records')
                else:
                    print(f"⚠️ Aucune donnée pour {date_str}")
                    return []
            else:
                print(f"⚠️ Colonne 'date' non trouvée")
                print(f"📊 Colonnes: {list(df.columns)}")
                return []
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return None
    
    @staticmethod
    def get_planning_stats():
        try:
            from gestion.models import PlanningExcel
            total = PlanningExcel.objects.count()
            active = PlanningExcel.objects.filter(est_actif=True).count()
            planning_actif = PlanningExcel.objects.filter(est_actif=True).first()
            
            return {
                'existe': total > 0,
                'total': total,
                'actif': active,
                'nom_fichier': planning_actif.nom_fichier if planning_actif else None,
                'nb_lignes': planning_actif.nombre_lignes if planning_actif else 0,
                'date_upload': planning_actif.date_upload.strftime('%d/%m/%Y %H:%M') if planning_actif else None,
                'dates_disponibles': json.loads(planning_actif.dates_disponibles) if planning_actif and planning_actif.dates_disponibles else []
            }
        except Exception as e:
            print(f"❌ Erreur stats: {e}")
            return {'existe': False, 'total': 0, 'actif': 0, 'nom_fichier': None, 'nb_lignes': 0, 'date_upload': None, 'dates_disponibles': []}