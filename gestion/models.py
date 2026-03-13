from django.db import models
from django.utils import timezone
from django.conf import settings

class Societe(models.Model):
    nom = models.CharField(max_length=200, unique=True, verbose_name="Nom de la société")
    matricule_fiscale = models.CharField(max_length=100, blank=True, null=True, verbose_name="Matricule fiscale")
    adresse = models.TextField(blank=True, null=True, verbose_name="Adresse de la société")
    telephone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone de la société")
    email = models.EmailField(blank=True, null=True, verbose_name="Email de la société")
    contact_personne = models.CharField(max_length=200, blank=True, null=True, verbose_name="Personne à contacter")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Société"
        verbose_name_plural = "Sociétés"
        ordering = ['nom']
    
    def __str__(self):
        return self.nom
    
    def get_agents_count(self):
        return self.agent_set.count()
    
    def get_affectations_count(self):
        from .models import Affectation
        return Affectation.objects.filter(agent__societe=self).count()

class Chauffeur(models.Model):
    TYPE_CHOICES = [
        ('taxi', 'Taxi'),
        ('prive', 'Chauffeur Privé'),
        ('societe', 'Chauffeur Société'),
    ]
    super_chauffeur = models.BooleanField(
        default=False,
        verbose_name="Super chauffeur (peut voir tous les chauffeurs)",
        help_text="Si coché, ce chauffeur peut voir tous les chauffeurs et leurs courses"
    )    
    nom = models.CharField(max_length=200)
    type_chauffeur = models.CharField(max_length=20, choices=TYPE_CHOICES, default='prive')
    telephone = models.CharField(max_length=20)
    numero_identite = models.CharField(max_length=50, blank=True, null=True)
    numero_voiture = models.CharField(max_length=50, blank=True, null=True)
    societe = models.CharField(max_length=100, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True, verbose_name="Adresse complète")
    email = models.EmailField(blank=True, null=True, verbose_name="Adresse email")
    prix_course_par_defaut = models.DecimalField(max_digits=10, decimal_places=2, default=10.0)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    # CORRECTION ICI : RENOMMEZ LE CHAMP POUR ÉVITER LA CONFUSION
    mobile_password = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Mot de passe mobile",
        help_text="Mot de passe pour l'application mobile (sera automatiquement hashé en SHA256)"
    )
    
    statut = models.CharField(max_length=20, default='actif', choices=[
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
        ('en_conge', 'En congé'),
    ])
    super_chauffeur = models.BooleanField(default=False, verbose_name="Super chauffeur")
    # UNE SEULE MÉTHODE set_mobile_password
    def set_mobile_password(self, raw_password):
      
        import hashlib
        if raw_password:
            raw_password = str(raw_password).strip()
            # Hasher le mot de passe
            self.mobile_password = hashlib.sha256(raw_password.encode()).hexdigest()
            print(f"🔧 set_mobile_password: '{raw_password}' -> {self.mobile_password}")
    
    def check_mobile_password(self, raw_password):
       
        import hashlib
        if not self.mobile_password or not raw_password:
            return False
        
        # Hasher le mot de passe fourni
        password_hash = hashlib.sha256(str(raw_password).encode()).hexdigest()
        
        # Comparer avec le hash stocké
        return self.mobile_password == password_hash
    
    def save(self, *args, **kwargs):
        # Vérifier si c'est une mise à jour (l'objet existe déjà en DB)
        is_update = self.pk is not None
        
        if is_update:
            # Récupérer l'ancienne version pour comparer
            try:
                old_chauffeur = Chauffeur.objects.get(pk=self.pk)
                old_password = old_chauffeur.mobile_password
            except Chauffeur.DoesNotExist:
                old_password = None
        else:
            old_password = None
        
        # ========== HASHAGE AUTOMATIQUE ==========
        # Si mobile_password existe et n'est pas déjà hashé
        if self.mobile_password and self.mobile_password.strip():
            # Vérifier si c'est déjà un hash SHA256 (64 caractères hexa)
            if len(self.mobile_password.strip()) != 64 or not all(c in '0123456789abcdefABCDEF' for c in self.mobile_password.strip()):
                import hashlib
                self.mobile_password = hashlib.sha256(self.mobile_password.strip().encode()).hexdigest()
                print(f"🔐 Mot de passe hashé pour {self.nom}")
        
        # ========== DÉCONNEXION SI MOT DE PASSE CHANGE ==========
        if is_update and old_password and self.mobile_password != old_password:
            print(f"🚨 Mot de passe changé pour {self.nom} - Déconnexion en cours...")
            
            try:
                from django.contrib.sessions.models import Session
                from django.utils import timezone
                
                # Chercher toutes les sessions actives de ce chauffeur
                sessions = Session.objects.filter(expire_date__gt=timezone.now())
                sessions_deleted = 0
                
                for session in sessions:
                    try:
                        session_data = session.get_decoded()
                        # Vérifier si c'est une session mobile de ce chauffeur
                        if session_data.get('chauffeur_id') == self.id:
                            session.delete()
                            sessions_deleted += 1
                    except Exception as e:
                        print(f"  ⚠️ Erreur session {session.session_key[:10]}: {e}")
                        continue
                
                if sessions_deleted > 0:
                    print(f"  ✅ {sessions_deleted} session(s) mobile supprimée(s)")
                else:
                    print(f"  ℹ️ Aucune session active trouvée")
                    
            except Exception as e:
                print(f"⚠️ Erreur lors de la déconnexion: {e}")
        # =======================================================
        
        # Sauvegarder l'objet
        super().save(*args, **kwargs)
    
    def force_logout_all_devices(self):
   
        try:
            from django.contrib.sessions.models import Session
            from django.utils import timezone
        
            sessions_deleted = 0
            sessions = Session.objects.filter(expire_date__gt=timezone.now())
        
            for session in sessions:
                try:
                    session_data = session.get_decoded()
                    if session_data.get('mobile_chauffeur_id') == self.id or                        session_data.get('chauffeur_id') == self.id:
                        session.delete()
                        sessions_deleted += 1
                except:
                    continue
        
            print(f"✅ {sessions_deleted} session(s) supprimée(s) pour {self.nom}")
            return sessions_deleted
        
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return 0
    def vehicule_info(self):
        if self.numero_voiture:
            return f"{self.get_type_chauffeur_display()} - {self.numero_voiture}"
        return self.get_type_chauffeur_display()
    
    class Meta:
        verbose_name = "Chauffeur"
        verbose_name_plural = "Chauffeurs"
        ordering = ['nom']
    
    def __str__(self):
        return f"{self.nom} ({self.get_type_chauffeur_display()})"

class HeureTransport(models.Model):
    TYPE_CHOICES = [
        ('ramassage', 'Ramassage'),
        ('depart', 'Départ'),
    ]
    
    type_transport = models.CharField(max_length=20, choices=TYPE_CHOICES)
    heure = models.IntegerField(help_text="Heure au format 24h (ex: 6 pour 6h, 22 pour 22h)")
    libelle = models.CharField(max_length=50, help_text="Libellé affiché (ex: 'Ramassage 6h')")
    active = models.BooleanField(default=True)
    ordre = models.IntegerField(default=0, help_text="Ordre d'affichage")
    
    class Meta:
        verbose_name = "Heure de transport"
        verbose_name_plural = "Heures de transport"
        ordering = ['type_transport', 'ordre', 'heure']
    
    def __str__(self):
        return f"{self.get_type_transport_display()} - {self.libelle}"

class Agent(models.Model):
    nom = models.CharField(max_length=200, unique=True)
    adresse = models.TextField()
    telephone = models.CharField(max_length=20)
    societe = models.ForeignKey(Societe, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Société")
    societe_texte = models.CharField(max_length=100, blank=True, null=True)
    voiture_personnelle = models.BooleanField(default=False)
    
    latitude = models.FloatField(null=True, blank=True, verbose_name="Latitude")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Longitude")
    adresse_geocodee = models.TextField(blank=True, null=True, verbose_name="Adresse géocodée")
    derniere_geolocalisation = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    date_correction_coords = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Date de correction des coordonnées"
    )
    corrige_manuellement = models.BooleanField(
        default=False,
        verbose_name="Coordonnées corrigées manuellement"
    )
    notes_correction = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Notes sur la correction"
    )
    
    def save(self, *args, **kwargs):
        # Si les coordonnées changent, marquer comme corrigé manuellement
        if self.pk:
            old_agent = Agent.objects.get(pk=self.pk)
            if (old_agent.latitude != self.latitude or 
                old_agent.longitude != self.longitude):
                self.corrige_manuellement = True
                from django.utils import timezone
                self.date_correction_coords = timezone.now()
        
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = "Agent"
        verbose_name_plural = "Agents"
        ordering = ['nom']
    
    def __str__(self):
        return self.nom
    
    def get_societe_display(self):
        if self.societe:
            return self.societe.nom
        return self.societe_texte or "Non spécifié"
    
    def est_complet(self):
        adresse_incomplete = self.adresse in ['Adresse à compléter', 'Adresse non renseignee', '']
        telephone_incomplete = self.telephone in ['00000000', 'Telephone non renseigne', '']
        societe_incomplete = not self.societe and not self.societe_texte
        
        return not (adresse_incomplete or telephone_incomplete or societe_incomplete)
    
    def geolocaliser(self):
        try:
            from gestion.geolocalisation.utils import GeolocalisationManager
            geo_manager = GeolocalisationManager()
            result = geo_manager.geocode_adresse(self.adresse)
            
            if result['success']:
                self.latitude = result['latitude']
                self.longitude = result['longitude']
                self.adresse_geocodee = result['adresse_formatee']
                self.derniere_geolocalisation = timezone.now()
                self.save()
                return True
            return False
        except Exception as e:
            print(f"Erreur géolocalisation pour {self.nom}: {e}")
            return False
    def corriger_adresse_pour_geolocalisation(self):
        
        if not self.adresse:
            return False
            
        # Liste des corrections d'adresses
        corrections = {
            'hay riadh': 'Hay Riadh, Sousse, Tunisie',
            'cite ghodrane': 'Cite Ghodrane, Sousse, Tunisie',
            'ariana ville': 'Ariana Ville, Sousse, Tunisie',
            'lac 2': 'Lac 2, Sousse, Tunisie',
            'ghodrane': 'Cite Ghodrane, Sousse, Tunisie',
            'riadh': 'Hay Riadh, Sousse, Tunisie',
            'lac': 'Lac 2, Sousse, Tunisie'
        }
        
        adresse_lower = self.adresse.lower()
        
        for mot_cle, adresse_corrigee in corrections.items():
            if mot_cle in adresse_lower:
                self.adresse = adresse_corrigee
                self.save()
                print(f"✅ Adresse corrigée: {self.nom} → {adresse_corrigee}")
                return True
        
        return False
class Course(models.Model):
    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.CASCADE)
    type_transport = models.CharField(max_length=20, choices=[('ramassage', 'Ramassage'), ('depart', 'Depart')])
    heure = models.IntegerField()
    jour = models.CharField(max_length=20)
    date_reelle = models.DateField()
    prix_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    statut = models.CharField(
        max_length=20, 
        default='en_attente',
        choices=[
            ('en_attente', 'En attente'),
            ('terminee', 'Terminée'),
            ('validee', 'Validée'),
            ('annulee', 'Annulée'),                  
            ('refusee', 'Refusée'),  # AJOUTÉ pour mobile
        ]
    )
  # ===== AJOUTEZ CES LIGNES POUR LE POINT DE DÉPART =====
    point_depart_latitude = models.FloatField(default=35.8342, blank=True, null=True, verbose_name="Latitude départ")
    point_depart_longitude = models.FloatField(default=10.6296, blank=True, null=True, verbose_name="Longitude départ")
    point_depart_adresse = models.TextField(
        default="rue rabat complexe zaoui sousse 4000", 
        blank=True, 
        null=True,
        verbose_name="Adresse de départ"
    )
    demande_validation_at = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Date de demande validation"
    )
    validee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='courses_validees',
        verbose_name="Validée par"
    )
    validee_at = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Date de validation"
    )
    notes_validation = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Notes de validation"
    )
    # ======================================================
    created_at = models.DateTimeField(default=timezone.now)
    
    # ************ SEULES AJOUTS REQUIS ************
    notes_validation = models.TextField(blank=True, null=True)  # AJOUTÉ
    demande_validation_at = models.DateTimeField(blank=True, null=True)  # AJOUTÉ
    validee_at = models.DateTimeField(blank=True, null=True)  # AJOUTÉ
    # *********************************************
    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        unique_together = ['chauffeur', 'heure', 'type_transport', 'jour', 'date_reelle']
    
    def __str__(self):
        return f"{self.chauffeur.nom} - {self.jour} {self.date_reelle} - {self.heure}h"
    
    def get_prix_course(self):
        # Utiliser le prix défini dans le chauffeur, sinon les prix par défaut
        if self.chauffeur.prix_course_par_defaut and   self.chauffeur.prix_course_par_defaut > 0:
            return self.chauffeur.prix_course_par_defaut
        else:
            # Fallback aux prix par défaut selon le type
            if self.chauffeur.type_chauffeur == 'taxi':
                return getattr(settings, 'PRIX_COURSE_TAXI', 15.0)
            elif self.chauffeur.type_chauffeur == 'prive':
                return getattr(settings, 'PRIX_COURSE_CHAUFFEUR', 10.0)
            else:
                return getattr(settings, 'PRIX_COURSE_SOCIETE', 0.0)    
    def get_societes_dans_course(self):
        societes = set()
        for affectation in self.affectation_set.all():
            societe_nom = affectation.agent.get_societe_display()
            if societe_nom and societe_nom != "Non spécifié":
                societes.add(societe_nom)
        return list(societes)

    def get_prix_par_societe(self):
        societes = self.get_societes_dans_course()
        if not societes:
            return 0.0
        
        prix_course = self.get_prix_course()
        if prix_course == 0:
            return 0.0
        
        return prix_course / len(societes)

       
    def demander_validation(self, notes=""):
       
        from django.utils import timezone
        self.statut = 'demande_validation'
        self.notes_validation = notes
        self.demande_validation_at = timezone.now()
        self.save()
        return True
    
    def valider_par_admin(self, notes=""):
        
        from django.utils import timezone
        self.statut = 'validee'
        self.notes_validation = notes
        self.validee_at = timezone.now()
        self.save()
        return True
    
    def marquer_comme_payee(self):
       
        if self.statut == 'validee':
            self.statut = 'payee'
            self.save()
            return True
        return False

    def refuser_par_admin(self, notes=""):
     
        from django.utils import timezone
        self.statut = 'refusee'
        self.notes_validation = notes
        self.save()
        return True
    
    def terminer_par_chauffeur(self):
        
        self.statut = 'terminee'
        self.save()
        return True
    
    def peut_etre_validee(self):
       
        return self.statut in ['en_attente', 'terminee']
    
    def est_en_attente_validation(self):
       
        return self.statut == 'demande_validation'

    def demander_validation(self, notes=""):
        
        from django.utils import timezone
        self.statut = 'demande_validation'
        self.notes_validation = notes
        self.demande_validation_at = timezone.now()
        self.save()
        return True
    
    def valider(self, user, notes=""):
       
        from django.utils import timezone
        self.statut = 'validee'
        self.validee_par = user
        self.validee_at = timezone.now()
        self.notes_validation = notes
        self.save()
        return True
    
    def refuser(self, notes=""):
        
        from django.utils import timezone
        self.statut = 'refusee'
        self.notes_validation = notes
        self.save()
        return True
    
    def annuler_validation(self):
       
        self.statut = 'en_attente'
        self.validee_par = None
        self.validee_at = None
        self.notes_validation = None
        self.save()
        return True
    
    def peut_etre_validee(self):
       
        return self.statut in ['en_attente', 'demande_validation', 'refusee']
    
    def est_validee(self):
       
        return self.statut == 'validee'
    
    def est_en_attente_validation(self):
       
        return self.statut == 'demande_validation'
# ============================================
# MODÈLE NOTIFICATION POUR ADMIN
# ============================================
class NotificationAdmin(models.Model):
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('danger', 'Urgent'),
        ('success', 'Succès'),
    ]
    
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lien = models.CharField(max_length=500, blank=True, null=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    date_creation = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
    lu_par = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Lu par"
    )
    date_lecture = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Notification Admin"
        verbose_name_plural = "Notifications Admin"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"[{self.get_type_display()}] {self.titre[:50]}"
    
    def marquer_comme_lu(self, user):
        from django.utils import timezone
        self.lu = True
        self.lu_par = user
        self.date_lecture = timezone.now()
        self.save()

class Reservation(models.Model):
   
    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.CASCADE, verbose_name="Chauffeur qui réserve")
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, verbose_name="Agent réservé")
    date_reservation = models.DateField(verbose_name="Date de la réservation (toujours J+1)")
    type_transport = models.CharField(max_length=20, choices=[
        ('ramassage', 'Ramassage'),
        ('depart', 'Départ')
    ], verbose_name="Type de transport")
    
    # RELATION vers HeureTransport (vos heures dynamiques)
    heure_transport = models.ForeignKey(
        'HeureTransport', 
        on_delete=models.CASCADE,
        verbose_name="Heure de transport",
        help_text="Heure configurée dynamiquement dans l'admin"
    )
    
    # Statuts de la réservation
    statut = models.CharField(max_length=20, default='reservee', choices=[
        ('reservee', 'Réservée'),
        ('confirmee', 'Confirmée'),
        ('annulee', 'Annulée'),
        ('terminee', 'Terminée'),
    ], verbose_name="Statut de la réservation")
    
    notes = models.TextField(blank=True, null=True, verbose_name="Notes du chauffeur")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Réservation J+1"
        verbose_name_plural = "Réservations J+1"
        unique_together = ['agent', 'date_reservation', 'heure_transport', 'type_transport']
        ordering = ['date_reservation', 'heure_transport__heure', 'chauffeur']
    
    def __str__(self):
        return f"{self.chauffeur.nom} → {self.agent.nom} ({self.date_reservation} - {self.heure_transport.libelle})"
    
    @property
    def heure_display(self):
        
        return self.heure_transport.libelle
    
    @property
    def heure_value(self):
       
        return self.heure_transport.heure

    def peut_etre_modifiee(self):
       
        from datetime import date
        # Une réservation peut être modifiée si elle est pour demain ou plus tard
        return self.date_reservation > date.today()
    
    def est_pour_demain(self):
       
        from datetime import date, timedelta
        demain = date.today() + timedelta(days=1)
        return self.date_reservation == demain

class Affectation(models.Model):
    TYPE_TRANSPORT_CHOICES = [
        ('ramassage', 'Ramassage'),
        ('depart', 'Depart'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.CASCADE, verbose_name="Chauffeur")
    heure = models.IntegerField()
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    type_transport = models.CharField(max_length=20, choices=TYPE_TRANSPORT_CHOICES)
    jour = models.CharField(max_length=20)
    date_reelle = models.DateField()
    prix_course = models.DecimalField(max_digits=10, decimal_places=0)
    prix_societe = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    date_ajout = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = "Affectation"
        verbose_name_plural = "Affectations"
        unique_together = [
            ['agent', 'date_reelle'],
            ['chauffeur', 'heure', 'agent', 'type_transport', 'jour', 'date_reelle']
        ]
    
    def __str__(self):
        return f"{self.chauffeur.nom} - {self.agent.nom} - {self.jour}"
    
    def save(self, *args, **kwargs):
        if self.course:
            self.prix_societe = self.course.get_prix_par_societe()
        super().save(*args, **kwargs)
# Ajoutez ceci dans gestion/models.py (à la fin du fichier)

    from django.db.models.signals import pre_delete
    from django.dispatch import receiver

    @receiver(pre_delete, sender=Chauffeur)
    def delete_chauffeur_sessions(sender, instance, **kwargs):
   
        print(f"🚨 Suppression du chauffeur {instance.nom} - Déconnexion des sessions...")
        try:
            from django.contrib.sessions.models import Session
            from django.utils import timezone
        
            sessions_deleted = 0
            sessions = Session.objects.filter(expire_date__gt=timezone.now())
        
            for session in sessions:
                try:
                    session_data = session.get_decoded()
                    if session_data.get('mobile_chauffeur_id') == instance.id:
                        session.delete()
                        sessions_deleted += 1
                except:
                    continue
        
            print(f"✅ {sessions_deleted} session(s) supprimée(s)")
        except Exception as e:
            print(f"❌ Erreur: {e}")
