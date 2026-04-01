import pandas as pd
import re
from datetime import datetime, timedelta
import os
import requests
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
            cache.set(cache_key, heures, 3600)
        return [(heure_obj.heure, heure_obj.libelle) for heure_obj in heures]
    
    def __init__(self, request=None):
        self.df_planning = None
        self.df_agents = None
        self.dates_par_jour = {}
        self.temp_path = os.path.join(settings.MEDIA_ROOT, 'temp_planning.xlsx')
        self._cache_transports = {}
        self.request = request
    
    def _lire_contenu_fichier(self, fichier):
        """Lit le contenu d'un fichier quel que soit son type"""
        try:
            if hasattr(fichier, 'read'):
                content = fichier.read()
                if hasattr(fichier, 'seek'):
                    fichier.seek(0)
                return content
            elif isinstance(fichier, str) and fichier.startswith('http'):
                response = requests.get(fichier)
                response.raise_for_status()
                return response.content
            elif isinstance(fichier, str) and os.path.exists(fichier):
                with open(fichier, 'rb') as f:
                    return f.read()
            elif isinstance(fichier, bytes):
                return fichier
            elif hasattr(fichier, 'getvalue'):
                return fichier.getvalue()
            else:
                raise ValueError(f"Type de fichier non supporté: {type(fichier)}")
        except Exception as e:
            print(f"❌ Erreur lecture fichier: {e}")
            raise
    
    def charger_planning_depuis_url(self, url):
        """Charge le planning depuis une URL Cloudinary"""
        try:
            print(f"📂 Chargement du planning depuis Cloudinary: {url}")
            content = self._lire_contenu_fichier(url)
            
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            with open(self.temp_path, 'wb') as f:
                f.write(content)
            
            return self.charger_planning(content)
        except Exception as e:
            print(f"❌ Erreur chargement depuis URL: {e}")
            return False
    
    def charger_planning(self, fichier):
        """Charge le fichier Excel de planning"""
        try:
            print("📂 Chargement du planning...")
            
            content = self._lire_contenu_fichier(fichier)
            
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            with open(self.temp_path, 'wb') as f:
                f.write(content)
            
            self.extraire_dates_reelles(content)
            
            df = pd.read_excel(BytesIO(content), header=None, engine='openpyxl')
            
            header_row_idx = None
            for idx in range(min(5, len(df))):
                row = df.iloc[idx]
                for cell in row:
                    if pd.notna(cell) and isinstance(cell, str):
                        if 'salarié' in str(cell).lower() or 'salarie' in str(cell).lower():
                            header_row_idx = idx
                            break
                if header_row_idx is not None:
                    break
            
            if header_row_idx is not None:
                self.df_planning = pd.read_excel(
                    BytesIO(content), 
                    skiprows=header_row_idx + 1,
                    engine='openpyxl'
                )
            else:
                self.df_planning = df
            
            self.df_planning = self.df_planning.dropna(how='all').reset_index(drop=True)
            
            noms_colonnes = ['Salarie', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche', 'Qualification']
            if len(self.df_planning.columns) > len(noms_colonnes):
                self.df_planning = self.df_planning.iloc[:, :len(noms_colonnes)]
            elif len(self.df_planning.columns) < len(noms_colonnes):
                noms_colonnes = noms_colonnes[:len(self.df_planning.columns)]
            
            self.df_planning.columns = noms_colonnes
            
            self._cache_transports = {}
            
            print(f"✅ Planning chargé: {len(self.df_planning)} lignes")
            print(f"📅 Dates disponibles: {self.dates_par_jour}")
            return True
                
        except Exception as e:
            print(f"❌ Erreur chargement planning: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def charger_agents(self, fichier):
        """Charge le fichier Excel des agents (info.xlsx)"""
        try:
            print("📂 Chargement des agents...")
            
            content = self._lire_contenu_fichier(fichier)
            agents_path = os.path.join(settings.MEDIA_ROOT, 'temp_agents.xlsx')
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            with open(agents_path, 'wb') as f:
                f.write(content)
            
            df = pd.read_excel(BytesIO(content), engine='openpyxl')
            self.df_agents = df
            
            print(f"✅ Agents chargés: {len(df)} lignes")
            
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
        """Recharge le planning depuis la session (fichier local ou Cloudinary)"""
        try:
            if self.request and self.request.session.get('uploaded_file'):
                file_info = self.request.session.get('uploaded_file')
                cloudinary_url = file_info.get('cloudinary_url')
                
                if cloudinary_url:
                    print(f"📂 Rechargement depuis Cloudinary: {cloudinary_url}")
                    return self.charger_planning_depuis_url(cloudinary_url)
            
            if os.path.exists(self.temp_path):
                print(f"📂 Rechargement depuis fichier local: {self.temp_path}")
                return self.charger_planning(self.temp_path)
            else:
                print("⚠️ Aucun fichier planning trouvé")
                return False
        except Exception as e:
            print(f"❌ Erreur rechargement planning: {e}")
            return False
    
    def extraire_dates_reelles(self, fichier):
        """Extrait les dates réelles du fichier Excel"""
        try:
            print("📅 Tentative d'extraction des dates...")
            
            if isinstance(fichier, bytes):
                content = fichier
            else:
                content = self._lire_contenu_fichier(fichier)
            
            df_raw = pd.read_excel(BytesIO(content), header=None, engine='openpyxl')
            
            print(f"📊 Structure du fichier: {len(df_raw)} lignes, {len(df_raw.columns)} colonnes")
            
            header_row_idx = None
            for idx in range(min(5, len(df_raw))):
                row = df_raw.iloc[idx]
                for cell in row:
                    if pd.notna(cell) and isinstance(cell, str):
                        if 'salarié' in str(cell).lower() or 'salarie' in str(cell).lower():
                            header_row_idx = idx
                            print(f"✅ Ligne des en-têtes trouvée à l'index {idx}")
                            break
                if header_row_idx is not None:
                    break
            
            if header_row_idx is None:
                print("⚠️ Ligne des en-têtes non trouvée, recherche alternative...")
                for idx in range(min(10, len(df_raw))):
                    row = df_raw.iloc[idx]
                    date_count = 0
                    for cell in row:
                        if pd.notna(cell):
                            cell_str = str(cell)
                            if re.search(r'\d{1,2}[\/\-]\d{1,2}', cell_str):
                                date_count += 1
                    if date_count >= 3:
                        header_row_idx = idx
                        print(f"✅ Ligne avec dates trouvée à l'index {idx}")
                        break
            
            if header_row_idx is not None:
                header_row = df_raw.iloc[header_row_idx]
                jours_ordre = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
                
                for col_idx in range(1, min(8, len(header_row))):
                    cell_value = header_row[col_idx]
                    if pd.notna(cell_value):
                        cell_str = str(cell_value).strip()
                        jour_nom = jours_ordre[col_idx - 1]
                        print(f"  {jour_nom} (colonne {col_idx}): '{cell_str}'")
                        
                        date_match = re.search(r'(\d{1,2}[\/\-]\d{1,2})', cell_str)
                        if date_match:
                            date_str = date_match.group(1)
                            try:
                                date_obj = datetime.strptime(f"{date_str}/2026", "%d/%m/%Y")
                                self.dates_par_jour[jour_nom] = date_obj.strftime("%d/%m/%Y")
                                print(f"    ✅ Date extraite: {self.dates_par_jour[jour_nom]}")
                            except:
                                try:
                                    date_obj = datetime.strptime(f"{date_str}/{datetime.now().year}", "%d/%m/%Y")
                                    self.dates_par_jour[jour_nom] = date_obj.strftime("%d/%m/%Y")
                                    print(f"    ✅ Date extraite (année courante): {self.dates_par_jour[jour_nom]}")
                                except:
                                    print(f"    ⚠️ Impossible de parser: {date_str}")
            else:
                print("⚠️ Aucune ligne d'en-tête trouvée")
            
            if not self.dates_par_jour:
                print("⚠️ Aucune date extraite, génération automatique...")
                self.generer_dates_par_defaut()
            else:
                print(f"📅 Dates extraites: {self.dates_par_jour}")
            
            return self.dates_par_jour
                
        except Exception as e:
            print(f"❌ Erreur extraction dates: {e}")
            import traceback
            traceback.print_exc()
            self.generer_dates_par_defaut()
            return self.dates_par_jour
    
    def generer_dates_par_defaut(self):
        """Génère des dates par défaut"""
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
        """Récupère les informations d'un agent"""
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
        """Extrait les créneaux horaires"""
        if pd.isna(planning_str) or str(planning_str).strip() in ['', 'REPOS', 'ABSENCE', 'OFF', 'MALADIE', 'CONGÉ PAYÉ', 'CONGÉ MATERNITÉ']:
            return []
        
        texte = str(planning_str).strip().upper()
        
        texte = re.sub(r'CH\s+', ' ', texte)
        texte = re.sub(r'R\s+', ' ', texte)
        texte = re.sub(r'F\s+', ' ', texte)
        texte = re.sub(r'V\s+', ' ', texte)
        texte = re.sub(r'[^0-9H\s\-:]', ' ', texte)
        texte = re.sub(r'\s+', ' ', texte).strip()
        
        patterns = [
            r'(\d{1,2})H?\s*[-]\s*(\d{1,2})H?',
            r'(\d{1,2})\s*[-]\s*(\d{1,2})',
        ]
        
        creneaux = []
        for pattern in patterns:
            matches = re.findall(pattern, texte)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    try:
                        heure_debut = int(match[0])
                        heure_fin = int(match[1])
                        
                        if heure_debut > 23:
                            continue
                        if heure_fin > 27:
                            continue
                        
                        if heure_fin < heure_debut and heure_fin < 12:
                            heure_fin += 24
                        
                        if (heure_debut, heure_fin) not in creneaux:
                            creneaux.append((heure_debut, heure_fin))
                    except:
                        continue
        
        if not creneaux:
            heures_trouvees = re.findall(r'\b\d{1,2}\b', texte)
            if len(heures_trouvees) >= 2:
                for i in range(0, len(heures_trouvees) - 1, 2):
                    try:
                        heure_debut = int(heures_trouvees[i])
                        heure_fin = int(heures_trouvees[i + 1])
                        
                        if heure_debut > 23 or heure_fin > 27:
                            continue
                        if heure_fin < heure_debut and heure_fin < 12:
                            heure_fin += 24
                        
                        if (heure_debut, heure_fin) not in creneaux:
                            creneaux.append((heure_debut, heure_fin))
                    except:
                        continue
        
        if len(creneaux) > 5:
            creneaux = creneaux[:5]
        
        return creneaux
    
    def _preparer_tous_les_transports(self):
        """Prépare tous les transports en une seule passe - avec normalisation des heures"""
        if self.df_planning is None or self.df_planning.empty:
            return {}
        
        cache_key = f"tous_transports_{hash(str(self.dates_par_jour))}"
        
        if cache_key in self._cache_transports:
            return self._cache_transports[cache_key]
        
        print("📊 Préparation de tous les transports...")
        
        transports_par_heure = {}
        
        for idx, agent in self.df_planning.iterrows():
            if pd.isna(agent.get('Salarie')) or str(agent['Salarie']).strip() == '':
                continue
            
            nom_agent = str(agent['Salarie']).strip()
            info_agent = self.get_info_agent(nom_agent)
            
            if info_agent['voiture_personnelle']:
                continue
            
            for jour_col, jour_nom in [('Lundi', 'Lundi'), ('Mardi', 'Mardi'), ('Mercredi', 'Mercredi'), 
                                        ('Jeudi', 'Jeudi'), ('Vendredi', 'Vendredi'), ('Samedi', 'Samedi'), 
                                        ('Dimanche', 'Dimanche')]:
                if jour_col not in agent.index:
                    continue
                
                planning = agent[jour_col]
                creneaux = self.extraire_heures(planning)
                
                for heure_debut, heure_fin in creneaux:
                    # Normalisation pour le ramassage
                    heure_debut_norm = heure_debut
                    if heure_debut_norm >= 24:
                        heure_debut_norm = heure_debut_norm - 24
                    if heure_debut_norm > 23:
                        continue
                    
                    # Ramassage
                    key_ramassage = (jour_nom, heure_debut_norm, 'ramassage')
                    if key_ramassage not in transports_par_heure:
                        transports_par_heure[key_ramassage] = []
                    # Éviter les doublons
                    if not any(a['agent'] == nom_agent for a in transports_par_heure[key_ramassage]):
                        transports_par_heure[key_ramassage].append({
                            'agent': nom_agent,
                            'agent_id': info_agent['agent_obj'].id if info_agent['agent_obj'] else None,
                            'adresse': info_agent['adresse'],
                            'telephone': info_agent['telephone'],
                            'societe': info_agent['societe'],
                            'est_complet': info_agent['est_complet']
                        })
                    
                    # Normalisation pour le départ
                    heure_fin_norm = heure_fin
                    if heure_fin_norm >= 24:
                        heure_fin_norm = heure_fin_norm - 24
                    if heure_fin_norm > 23:
                        continue
                    
                    # Départ
                    key_depart = (jour_nom, heure_fin_norm, 'depart')
                    if key_depart not in transports_par_heure:
                        transports_par_heure[key_depart] = []
                    # Éviter les doublons
                    if not any(a['agent'] == nom_agent for a in transports_par_heure[key_depart]):
                        transports_par_heure[key_depart].append({
                            'agent': nom_agent,
                            'agent_id': info_agent['agent_obj'].id if info_agent['agent_obj'] else None,
                            'adresse': info_agent['adresse'],
                            'telephone': info_agent['telephone'],
                            'societe': info_agent['societe'],
                            'est_complet': info_agent['est_complet']
                        })
        
        self._cache_transports[cache_key] = transports_par_heure
        
        # Afficher les heures disponibles pour déboguer
        heures_disponibles = {}
        for (jour, heure, type_t) in transports_par_heure.keys():
            if heure not in heures_disponibles:
                heures_disponibles[heure] = []
            heures_disponibles[heure].append(type_t)
        
        print(f"✅ Préparation terminée: {len(transports_par_heure)} créneaux")
        print(f"📊 Heures disponibles: {sorted(heures_disponibles.keys())}")
        
        return transports_par_heure
    
    def traiter_donnees(self, filtre_form):
        """Traite les données du planning avec les filtres - avec filtrage par heure spécifique"""
        if self.df_planning is None or self.df_planning.empty:
            print("❌ df_planning est None ou vide")
            return []
        
        jour_selectionne = filtre_form.cleaned_data.get('jour', 'Tous')
        type_transport_selectionne = filtre_form.cleaned_data.get('type_transport', 'tous')
        heure_ete_active = filtre_form.cleaned_data.get('heure_ete', False)
        filtre_agents = filtre_form.cleaned_data.get('filtre_agents', 'tous')

        # Récupérer l'heure spécifique si elle existe
        heure_specifique = None
        if hasattr(filtre_form, 'data') and filtre_form.data:
            heure_specifique_str = filtre_form.data.get('heure_specifique', '')
            if heure_specifique_str:
                try:
                    heure_specifique = int(heure_specifique_str)
                    print(f"🎯 Heure spécifique demandée: {heure_specifique}h")
                except:
                    pass
        
        heures_ramassage = []
        heures_depart = []
        
        if type_transport_selectionne in ['tous', 'ramassage']:
            heures_ramassage = [h for h, _ in self.get_heures_config('ramassage')]
        if type_transport_selectionne in ['tous', 'depart']:
            heures_depart = [h for h, _ in self.get_heures_config('depart')]

        # Si une heure spécifique est demandée, filtrer uniquement cette heure
        if heure_specifique is not None:
            if type_transport_selectionne in ['tous', 'ramassage']:
                if heure_specifique in heures_ramassage:
                    heures_ramassage = [heure_specifique]
                else:
                    heures_ramassage = []
            if type_transport_selectionne in ['tous', 'depart']:
                if heure_specifique in heures_depart:
                    heures_depart = [heure_specifique]
                else:
                    heures_depart = []
            print(f"🎯 Filtrage sur heure spécifique: ramassage={heures_ramassage}, depart={heures_depart}")    
        
        tous_transports = self._preparer_tous_les_transports()
        
        liste_transports = []
        
        for (jour, heure, type_transport), agents in tous_transports.items():
            # Filtrer par jour
            if jour_selectionne != 'Tous' and jour != jour_selectionne:
                continue
            
            # Filtrer par type de transport
            if type_transport_selectionne != 'tous' and type_transport != type_transport_selectionne:
                continue
            
            # Filtrer par heure (CRITIQUE pour le filtrage spécifique)
            if type_transport == 'ramassage' and heure not in heures_ramassage:
                continue
            if type_transport == 'depart' and heure not in heures_depart:
                continue
            
            # Ajustement heure d'été
            if heure_ete_active:
                heure_affichee = heure - 1
                if heure_affichee < 0:
                    heure_affichee += 24
            else:
                heure_affichee = heure
            
            # Ajouter les transports
            for agent_data in agents:
                if filtre_agents == 'complets' and not agent_data['est_complet']:
                    continue
                elif filtre_agents == 'incomplets' and agent_data['est_complet']:
                    continue
                
                liste_transports.append({
                    'agent': agent_data['agent'],
                    'jour': jour,
                    'heure': heure,
                    'heure_affichage': f"{heure_affichee}h",
                    'adresse': agent_data['adresse'],
                    'telephone': agent_data['telephone'],
                    'societe': agent_data['societe'],
                    'date_reelle': self.dates_par_jour.get(jour, 'Date non definie'),
                    'type_transport': type_transport,
                    'est_complet': agent_data['est_complet'],
                    'agent_id': agent_data['agent_id']
                })
        
        # Trier
        ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        liste_transports.sort(key=lambda x: (ordre_jours.index(x['jour']), x['type_transport'], x['heure']))
        
        print(f"✅ {len(liste_transports)} transports trouvés pour les heures: ramassage={heures_ramassage}, depart={heures_depart}")
        
        # Afficher les premières heures trouvées pour déboguer
        if liste_transports:
            heures_trouvees = set()
            for t in liste_transports[:20]:
                heures_trouvees.add((t['heure'], t['type_transport']))
            print(f"   Heures trouvées: {sorted(heures_trouvees)}")
        
        return liste_transports

    def get_agents_non_affectes(self, jour, type_transport, heure, date_reelle):
        """Retourne les agents non encore affectés"""
        try:
            date_obj = datetime.strptime(date_reelle, "%d/%m/%Y").date()
            
            agents_affectes = Affectation.objects.filter(
                jour=jour,
                type_transport=type_transport,
                heure=heure,
                date_reelle=date_obj
            ).values_list('agent__nom', flat=True)
            
            agents_non_affectes = []
            
            if self.df_planning is not None:
                for index, agent in self.df_planning.iterrows():
                    if pd.isna(agent['Salarie']) or str(agent['Salarie']).strip() == '':
                        continue
                    
                    nom_agent = str(agent['Salarie']).strip()
                    
                    if nom_agent not in agents_affectes:
                        info_agent = self.get_info_agent(nom_agent)
                        if not info_agent['voiture_personnelle']:
                            agents_non_affectes.append(nom_agent)
            
            return agents_non_affectes
            
        except Exception as e:
            print(f"Erreur get_agents_non_affectes: {e}")
            return []
    
    def verifier_date_dans_planning(self, date_cible):
        """Vérifie si une date est présente dans le planning"""
        if not self.dates_par_jour:
            return False, "Aucune date extraite du planning"
        
        jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        jour_semaine_cible = jours_fr[date_cible.weekday()]
        
        if jour_semaine_cible not in self.dates_par_jour:
            dates_disponibles = "\n".join([f"• {jour}: {date}" for jour, date in self.dates_par_jour.items()])
            error_msg = (
                f"{jour_semaine_cible} non présent dans le planning.\n\n"
                f"Dates disponibles :\n"
                f"{dates_disponibles}\n\n"
                f"Veuillez charger un fichier contenant le {jour_semaine_cible} {date_cible.strftime('%d/%m/%Y')}."
            )
            return False, error_msg
        
        date_str = self.dates_par_jour[jour_semaine_cible]
        try:
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
            return True, f"{jour_semaine_cible} présent dans le planning"