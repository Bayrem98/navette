# Modèles pour l'interface mobile
from django.db import models
from django.utils import timezone
# Dans le modèle MobileNotification
class MobileNotification(models.Model):
    TYPE_CHOICES = [
        ('reservation', 'Nouvelle réservation'),
        ('annulation', 'Annulation de réservation'),
        ('info', 'Information'),
        ('alerte', 'Alerte'),
        ('super_reservation', 'Réservation par Super Chauffeur'),
        ('super_annulation', 'Annulation par Super Chauffeur'),
        ('agent_selection', 'Agent à transporter'),  # NOUVEAU TYPE
        ('transport_confirmation', 'Confirmation transport'),  # NOUVEAU TYPE
    ]
    
    chauffeur = models.ForeignKey('gestion.Chauffeur', on_delete=models.CASCADE, related_name='notifications_mobile')
    type_notification = models.CharField(max_length=25, choices=TYPE_CHOICES)
    message = models.TextField()
    vue = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(default=dict, blank=True)
    
    # NOUVEAUX CHAMPS POUR LE GROUPEMENT
    heure_transport = models.ForeignKey('gestion.HeureTransport', on_delete=models.SET_NULL, 
                                        null=True, blank=True, related_name='notifications')
    date_transport = models.DateField(null=True, blank=True)
    type_transport = models.CharField(max_length=20, choices=[
        ('ramassage', 'Ramassage'),
        ('depart', 'Départ'),
        ('', 'Non spécifié')
    ], default='', blank=True)
    groupe_notification = models.CharField(max_length=100, blank=True, 
                                         help_text="Clé pour grouper les notifications par heure")
    
    class Meta:
        verbose_name = "Notification mobile"
        verbose_name_plural = "Notifications mobiles"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['groupe_notification', '-created_at']),
            models.Index(fields=['chauffeur', 'vue', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.chauffeur.nom} - {self.message[:50]}"
    
    def mark_as_read(self):
        self.vue = True
        self.save()
    
    def save(self, *args, **kwargs):
        # Générer une clé de groupe si non spécifiée
        if not self.groupe_notification and self.date_transport and self.heure_transport:
            self.groupe_notification = f"{self.date_transport}_{self.heure_transport.id}"
        super().save(*args, **kwargs)

class MobileCourseStatus(models.Model):
    
    STATUS_CHOICES = [
        ('a_faire', 'À faire'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('validee', 'Validée'),
        ('probleme', 'Problème'),
    ]
    
    course = models.ForeignKey('gestion.Course', on_delete=models.CASCADE)
    chauffeur = models.ForeignKey('gestion.Chauffeur', on_delete=models.CASCADE)
    statut_mobile = models.CharField(max_length=20, choices=STATUS_CHOICES, default='a_faire')
    heure_reelle = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Statut mobile"
        verbose_name_plural = "Statuts mobiles"
        unique_together = ['course', 'chauffeur']
    
    def __str__(self):
        return f"{self.course} - {self.get_statut_mobile_display()}"
