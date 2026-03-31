import pandas as pd
import re
from datetime import datetime, timedelta
import os
from io import BytesIO
from django.conf import settings
from django.core.cache import cache
from .models import HeureTransport, Affectation, Agent, Course, Societe

class GestionnaireTransport:
    def get_heures_config(self, type_transport):
        cache_key = f'heures_config_{type_transport}'
        heures = cache.get(cache_key)
        if not heures:
            heures = HeureTransport.objects.filter(
                type_transport=type_transport, 
                active=True
            ).order_by('ordre')
            cache.set(cache_key, heures, 3600)  # Cache 1 heure
        return [(heure_obj.heure, heure_obj.libelle) for heure_obj in heures]
    
    def __init__(self):
        self.df_planning = None
        self.df_agents = None
        self.dates_par_jour = {}
        self.temp_path = os.path.join(settings.MEDIA_ROOT, 'temp_planning.xlsx')
    
    def _lire_contenu_fichier(self, fichier):
        """
        Lit le contenu d'un fichier quel que soit son type:
        - UploadedFile (Django)
        - BufferedReader (open())
        - Chemin de fichier (str)
        - BytesIO
        Retourne le contenu binaire
        """
        try:
            # Cas 1: C'est un objet avec la méthode read()
            if hasattr(fichier, 'read'):
                # Lire le contenu
                content = fichier.read()
                # Réinitialiser le pointeur si possible
                if hasattr(fichier, 'seek'):
                    fichier.seek(0)
                return content
            
            # Cas 2: C'est un chemin de fichier (string)
            elif isinstance(fichier, str) and os.path.exists(fichier):
                with open(fichier, 'rb') as f:
                    return f.read()
            
            # Cas 3: C'est déjà des bytes
            elif isinstance(fichier, bytes):
                return fichier
            
            # Cas 4: C'est BytesIO
            elif hasattr(fichier, 'getvalue'):
                return fichier.getvalue()
            
            else:
                raise ValueError(f"Type de fichier non supporté: {type(fichier)}")
                
        except Exception as e:
            print(f"❌ Erreur lecture fichier: {e}")
            raise
    
    def charger_planning(self, fichier):
        """
        Charge le fichier Excel de planning
        Accepte: UploadedFile, chemin (str), BufferedReader, BytesIO
        """
        try:
            print("📂 Chargement du planning...")
            
            # Lire le contenu du fichier
            content = self._lire_contenu_fichier(fichier)
            
            # Sauvegarder localement si c'est un chemin ou un fichier uploadé
            if isinstance(fichier, str) and os.path.exists(fichier):
                # C'est déjà un chemin, on le garde
                pass
            else:
                # Sauvegarder pour usage futur
                os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
                with open(self.temp_path, 'wb') as f:
                    f.write(content)
            
            # Extraire les dates réelles
            self.extraire_dates_reelles(content)
            
            # Lire le fichier avec pandas
            df = pd.read_excel(BytesIO(content), engine='openpyxl')
            
            # Trouver la ligne de début des données
            ligne_debut = 0
            for idx in range(min(5, len(df))):
                row = df.iloc[idx]
                # Chercher la ligne avec "Salarié" ou des noms d'agents
                if any('Salarié' in str(cell) for cell in row if pd.notna(cell)):
                    ligne_debut = idx
                    break
                # Si on trouve un nom d'agent plausible
                if any(isinstance(cell, str) and len(cell) > 3 and ' ' in cell for cell in row if pd.notna(cell)):
                    ligne_debut = idx
                    break
            
            # Lire à partir de la ligne trouvée
            if ligne_debut > 0:
                self.df_planning = pd.read_excel(BytesIO(content), skiprows=ligne_debut, engine='openpyxl')
            else:
                self.df_planning = df
            
            # Nettoyer le dataframe
            self.df_planning = self.df_planning.dropna(how='all').reset_index(drop=True)
            
            # Renommer les colonnes
            noms_colonnes = ['Salarie', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche', 'Qualification']
            if len(self.df_planning.columns) > len(noms_colonnes):
                self.df_planning = self.df_planning.iloc[:, :len(noms_colonnes)]
            elif len(self.df_planning.columns) < len(noms_colonnes):
                noms_colonnes = noms_colonnes[:len(self.df_planning.columns)]
            
            self.df_planning.columns = noms_colonnes
            
            print(f"✅ Planning chargé: {len(self.df_planning)} lignes")
            return True
                
        except Exception as e:
            print(f"❌ Erreur chargement planning: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def charger_agents(self, fichier):
        """
        Charge le fichier Excel des agents (info.xlsx)
        Accepte: UploadedFile, chemin (str), BufferedReader, BytesIO
        """
        try:
            print("📂 Chargement des agents...")
            
            # Lire le contenu du fichier
            content = self._lire_contenu_fichier(fichier)
            
            # Sauvegarder localement si nécessaire
            agents_path = os.path.join(settings.MEDIA_ROOT, 'temp_agents.xlsx')
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            with open(agents_path, 'wb') as f:
                f.write(content)
            
            # Lire avec pandas
            df = pd.read_excel(BytesIO(content), engine='openpyxl')
            self.df_agents = df
            
            print(f"✅ Agents chargés: {len(df)} lignes")
            
            # Mettre à jour ou créer les agents dans la base
            for index, row in df.iterrows():
                nom = row.get('voyant', '')
                if nom and pd.notna(nom):
                    nom_str = str(nom).strip()
                    if not nom_str:
                        continue
                    
                    try:
                        agent, created = Agent.objects.get_or_create(
                            nom=nom_str,
                            defaults={
                                'adresse': str(row.get('adresse', 'Adresse à compléter')),
                                'telephone': str(row.get('Mobile', '00000000')),
                                'voiture_personnelle': str(row.get('voiture', '')).lower() in ['oui', 'yes', 'true', '1']
                            }
                        )
                        
                        # Mettre à jour la société si présente
                        societe_nom = row.get('societe', '')
                        if societe_nom and pd.notna(societe_nom):
                            societe_nom_str = str(societe_nom).strip()
                            if societe_nom_str:
                                societe_obj, _ = Societe.objects.get_or_create(
                                    nom=societe_nom_str,
                                    defaults={'adresse': '', 'telephone': ''}
                                )
                                agent.societe = societe_obj
                                agent.societe_texte = None
                                agent.save()
                                
                    except Exception as e:
                        print(f"⚠️ Erreur import agent {nom}: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur chargement agents: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def recharger_planning_depuis_session(self):
        """Recharge le planning depuis le fichier temporaire"""
        try:
            if os.path.exists(self.temp_path):
                return self.charger_planning(self.temp_path)
            else:
                print("⚠️ Fichier planning temporaire non trouvé")
                return False
        except Exception as e:
            print(f"❌ Erreur rechargement planning: {e}")
            return False
    
    def extraire_dates_reelles(self, fichier):
        """
        Extrait les dates réelles du fichier Excel
        Accepte: UploadedFile, chemin (str), BufferedReader, BytesIO, ou contenu bytes
        """
        try:
            print("📅 Tentative d'extraction des dates...")
            
            # Lire le contenu
            if isinstance(fichier, bytes):
                content = fichier
            else:
                content = self._lire_contenu_fichier(fichier)
            
            # Lire avec pandas
            df_raw = pd.read_excel(BytesIO(content), header=None, engine='openpyxl')
            
            # Chercher la ligne contenant les dates
            date_row_index = None
            for idx in range(min(5, len(df_raw))):
                row = df_raw.iloc[idx]
                date_count = 0
                for cell in row:
                    if pd.notna(cell):
                        cell_str = str(cell)
                        # Rechercher des motifs de date
                        if re.search(r'\d{1,2}[\/\-]\d{1,2}', cell_str) or isinstance(cell, (datetime, pd.Timestamp)):
                            date_count += 1
                
                if date_count >= 3:  # Si au moins 3 cellules semblent être des dates
                    date_row_index = idx
                    break
            
            # Mapping des colonnes vers les jours
            colonne_vers_jour = {
                1: 'Lundi', 2: 'Mardi', 3: 'Mercredi', 4: 'Jeudi',
                5: 'Vendredi', 6: 'Samedi', 7: 'Dimanche'
            }
            
            if date_row_index is not None:
                date_row = df_raw.iloc[date_row_index]
                print(f"📊 Ligne de dates trouvée à l'index {date_row_index}")
                
                for col_idx, jour_nom in colonne_vers_jour.items():
                    if col_idx < len(date_row):
                        cell_value = date_row[col_idx]
                        if pd.notna(cell_value):
                            try:
                                if isinstance(cell_value, (datetime, pd.Timestamp)):
                                    date_obj = cell_value
                                    self.dates_par_jour[jour_nom] = date_obj.strftime("%d/%m/%Y")
                                    print(f"  ✅ {jour_nom}: {self.dates_par_jour[jour_nom]}")
                                else:
                                    cell_str = str(cell_value).strip()
                                    # Essayer de parser
                                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y']:
                                        try:
                                            date_obj = datetime.strptime(cell_str, fmt)
                                            self.dates_par_jour[jour_nom] = date_obj.strftime("%d/%m/%Y")
                                            print(f"  ✅ {jour_nom}: {self.dates_par_jour[jour_nom]}")
                                            break
                                        except:
                                            continue
                            except Exception as e:
                                print(f"  ⚠️ {jour_nom}: conversion impossible - {e}")
            
            # Si aucune date extraite, générer par défaut
            if not self.dates_par_jour:
                print("⚠️ Aucune date extraite, génération automatique...")
                self.generer_dates_par_defaut()
            
            print(f"📅 Dates extraites: {self.dates_par_jour}")
            return self.dates_par_jour
                
        except Exception as e:
            print(f"❌ Erreur extraction dates: {e}")
            self.generer_dates_par_defaut()
            return self.dates_par_jour
    
    def generer_dates_par_defaut(self):
        """Génère des dates par défaut (lundi de la semaine courante)"""
        aujourd_hui = datetime.now()
        jours_ordre = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        
        jour_actuel = aujourd_hui.weekday()
        jours_vers_lundi = (0 - jour_actuel) % 7
        date_debut = aujourd_hui + timedelta(days=jours_vers_lundi)
        
        for i, jour in enumerate(jours_ordre):
            date_jour = date_debut + timedelta(days=i)
            self.dates_par_jour[jour] = date_jour.strftime("%d/%m/%Y")
        
        print(f"📅 Dates par défaut: {self.dates_par_jour}")
    
    def get_info_agent(self, nom_agent):
        """Récupère les informations d'un agent depuis la base"""
        try:
            agent_db = Agent.objects.filter(nom__icontains=nom_agent).first()
            if agent_db:
                return {
                    "adresse": agent_db.adresse,
                    "telephone": agent_db.telephone,
                    "societe": agent_db.get_societe_display(),
                    "voiture_personnelle": agent_db.voiture_personnelle,
                    "est_complet": agent_db.est_complet(),
                    "agent_obj": agent_db
                }
            else:
                agent = Agent.objects.create(
                    nom=nom_agent,
                    adresse="Adresse à compléter",
                    telephone="00000000",
                    societe_texte="Société à compléter",
                    voiture_personnelle=False
                )
                return {
                    "adresse": agent.adresse,
                    "telephone": agent.telephone,
                    "societe": agent.get_societe_display(),
                    "voiture_personnelle": agent.voiture_personnelle,
                    "est_complet": agent.est_complet(),
                    "agent_obj": agent
                }
        except Exception as e:
            print(f"Erreur recherche agent {nom_agent}: {e}")
            return {
                "adresse": "Adresse non renseignee",
                "telephone": "Telephone non renseigne", 
                "societe": "Societe non renseignee",
                "voiture_personnelle": False,
                "est_complet": False,
                "agent_obj": None
            }
    
    def extraire_heures(self, planning_str):
        """Extrait les créneaux horaires d'une chaîne de planning"""
        if pd.isna(planning_str) or str(planning_str).strip() in ['', 'REPOS', 'ABSENCE', 'OFF', 'MALADIE', 'CONGÉ PAYÉ', 'CONGÉ MATERNITÉ']:
            return []
        
        texte = str(planning_str).strip().upper()
        
        # Nettoyer le texte
        texte_propre = re.sub(r'[^0-9H\s\-:]', ' ', texte)
        texte_propre = re.sub(r'\s+', ' ', texte_propre).strip()
        
        # Patterns pour trouver les plages horaires
        patterns = [
            r'(\d{1,2})H?\s*[-]\s*(\d{1,2})H?',
            r'(\d{1,2})\s*[-]\s*(\d{1,2})',
        ]
        
        creneaux = []
        for pattern in patterns:
            matches = re.findall(pattern, texte_propre)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    heure_debut = int(match[0])
                    heure_fin = int(match[1])
                    
                    if heure_fin < heure_debut and heure_fin < 12:
                        heure_fin += 24
                    
                    creneaux.append((heure_debut, heure_fin))
        
        return creneaux
    
    def traiter_donnees(self, filtre_form):
        """Traite les données du planning avec les filtres"""
        if self.df_planning is None or self.df_planning.empty:
            print("❌ df_planning est None ou vide")
            return []
        
        liste_transports = []
        
        jour_selectionne = filtre_form.cleaned_data.get('jour', 'Tous')
        type_transport_selectionne = filtre_form.cleaned_data.get('type_transport', 'tous')
        heure_ete_active = filtre_form.cleaned_data.get('heure_ete', False)
        filtre_agents = filtre_form.cleaned_data.get('filtre_agents', 'tous')
        
        # Récupérer les heures configurées
        heures_ramassage = []
        heures_depart = []
        
        if type_transport_selectionne in ['tous', 'ramassage']:
            heures_ramassage = [h for h, _ in self.get_heures_config('ramassage')]
        if type_transport_selectionne in ['tous', 'depart']:
            heures_depart = [h for h, _ in self.get_heures_config('depart')]
        
        jours_mapping = {
            'Lundi': 'Lundi', 'Mardi': 'Mardi', 'Mercredi': 'Mercredi', 
            'Jeudi': 'Jeudi', 'Vendredi': 'Vendredi', 'Samedi': 'Samedi', 'Dimanche': 'Dimanche'
        }
        
        for index, agent in self.df_planning.iterrows():
            if pd.isna(agent.get('Salarie')) or str(agent['Salarie']).strip() == '':
                continue
            
            nom_agent = str(agent['Salarie']).strip()
            info_agent = self.get_info_agent(nom_agent)
            
            # Appliquer le filtre agents complet/incomplet
            if filtre_agents == 'complets' and not info_agent['est_complet']:
                continue
            elif filtre_agents == 'incomplets' and info_agent['est_complet']:
                continue
            
            # Exclure les agents avec voiture personnelle
            if info_agent['voiture_personnelle']:
                continue
            
            jours_a_verifier = []
            if jour_selectionne == 'Tous':
                for jour_col, jour_nom in jours_mapping.items():
                    if jour_col in agent.index:
                        jours_a_verifier.append((jour_col, jour_nom))
            else:
                if jour_selectionne in agent.index:
                    jours_a_verifier.append((jour_selectionne, jour_selectionne))
            
            for jour_col, jour_nom in jours_a_verifier:
                planning = agent[jour_col]
                creneaux = self.extraire_heures(planning)
                
                for heure_debut, heure_fin in creneaux:
                    if heure_ete_active:
                        heure_debut_ajustee = heure_debut - 1
                        heure_fin_ajustee = heure_fin - 1
                    else:
                        heure_debut_ajustee = heure_debut
                        heure_fin_ajustee = heure_fin
                    
                    # Ramassage
                    if type_transport_selectionne in ['tous', 'ramassage'] and heure_debut_ajustee in heures_ramassage:
                        liste_transports.append({
                            'agent': nom_agent,
                            'jour': jour_nom,
                            'heure': heure_debut_ajustee,
                            'heure_affichage': f"{heure_debut_ajustee}h",
                            'adresse': info_agent['adresse'],
                            'telephone': info_agent['telephone'],
                            'societe': info_agent['societe'],
                            'date_reelle': self.dates_par_jour.get(jour_nom, 'Date non definie'),
                            'type_transport': 'ramassage',
                            'est_complet': info_agent['est_complet'],
                            'agent_id': info_agent['agent_obj'].id if info_agent['agent_obj'] else None
                        })
                    
                    # Départ
                    heure_fin_comparaison = heure_fin_ajustee % 24
                    if type_transport_selectionne in ['tous', 'depart'] and heure_fin_comparaison in heures_depart:
                        heure_fin_affichee = heure_fin_ajustee % 24
                        liste_transports.append({
                            'agent': nom_agent,
                            'jour': jour_nom,
                            'heure': heure_fin_ajustee,
                            'heure_affichage': f"{heure_fin_affichee}h",
                            'adresse': info_agent['adresse'],
                            'telephone': info_agent['telephone'],
                            'societe': info_agent['societe'],
                            'date_reelle': self.dates_par_jour.get(jour_nom, 'Date non definie'),
                            'type_transport': 'depart',
                            'est_complet': info_agent['est_complet'],
                            'agent_id': info_agent['agent_obj'].id if info_agent['agent_obj'] else None
                        })
        
        # Trier par jour, type, heure
        ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        liste_transports.sort(key=lambda x: (ordre_jours.index(x['jour']), x['type_transport'], x['heure']))
        
        return liste_transports

    def get_agents_non_affectes(self, jour, type_transport, heure, date_reelle):
        "Retourne les agents non encore affectés pour ce jour/type/heure"
        try:
            # Convertir la date
            date_obj = datetime.strptime(date_reelle, "%d/%m/%Y").date()
            
            # Agents déjà affectés
            agents_affectes = Affectation.objects.filter(
                jour=jour,
                type_transport=type_transport,
                heure=heure,
                date_reelle=date_obj
            ).values_list('agent__nom', flat=True)
            
            # Filtrer les agents du planning qui ne sont pas encore affectés
            agents_non_affectes = []
            
            if self.df_planning is not None:
                for index, agent in self.df_planning.iterrows():
                    if pd.isna(agent['Salarie']) or str(agent['Salarie']).strip() == '':
                        continue
                    
                    nom_agent = str(agent['Salarie']).strip()
                    
                    # Vérifier si l'agent est déjà affecté
                    if nom_agent not in agents_affectes:
                        info_agent = self.get_info_agent(nom_agent)
                        
                        # Vérifier si l'agent a une voiture personnelle
                        if not info_agent['voiture_personnelle']:
                            agents_non_affectes.append(nom_agent)
            
            return agents_non_affectes
            
        except Exception as e:
            print(f"Erreur get_agents_non_affectes: {e}")
            return []
    def verifier_date_dans_planning(gestionnaire, date_cible):
    
        if not hasattr(gestionnaire, 'dates_extractees'):
            return False, "Aucune date extraite du planning"
    
        jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        jour_semaine_cible = jours_fr[date_cible.weekday()]
    
        dates_extractees = gestionnaire.dates_extractees
    
        # Vérifier si le jour de la semaine existe
        if jour_semaine_cible not in dates_extractees:
            dates_disponibles = "\n".join([f"• {jour}: {date}" for jour, date in dates_extractees.items()])
            error_msg = (
                f"{jour_semaine_cible} non présent dans le planning.\n\n"
                f"Dates disponibles :\n"
                f"{dates_disponibles}\n\n"
                f"Veuillez charger un fichier contenant le {jour_semaine_cible} {date_cible.strftime('%d/%m/%Y')}."
            )
            return False, error_msg
    
        # Vérifier si la date correspond
        date_str = dates_extractees[jour_semaine_cible]
        try:
            from datetime import datetime
            date_extracted = datetime.strptime(date_str, '%d/%m/%Y').date()
        
            if date_extracted != date_cible:
                error_msg = (
                    f"Décalage de dates détecté !\n\n"
                    f"Date recherchée : {date_cible.strftime('%d/%m/%Y')} ({jour_semaine_cible})\n"
                    f"Date dans Excel : {date_extracted.strftime('%d/%m/%Y')} ({jour_semaine_cible})\n\n"
                    f"Veuillez charger un fichier EMS.xlsx pour la semaine du {date_cible.strftime('%d/%m/%Y')}."
                )
                return False, error_msg
        
            return True, f"Date vérifiée : {date_cible.strftime('%d/%m/%Y')}"
        
        except ValueError:
            # Si le parsing échoue, on considère que c'est bon (format différent)
            return True, f"{jour_semaine_cible} présent dans le planning"

