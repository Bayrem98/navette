from django.contrib import admin
from django.http import HttpResponse
import pandas as pd
from io import BytesIO
from .models import Societe, Chauffeur, Agent, Affectation, HeureTransport, Course, Reservation
@admin.register(Societe)
class SocieteAdmin(admin.ModelAdmin):
    list_display = ['nom', 'matricule_fiscale', 'telephone', 'email', 'get_agents_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['nom', 'matricule_fiscale', 'adresse', 'telephone']
    list_editable = ['telephone', 'email']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('nom', 'matricule_fiscale')
        }),
        ('Coordonnées', {
            'fields': ('adresse', 'telephone', 'email', 'contact_personne')
        }),
    )
    
    def get_agents_count(self, obj):
        return obj.agent_set.count()
    get_agents_count.short_description = "Nb Agents"
    get_agents_count.admin_order_field = 'agent__count'  # Pour pouvoir trier
@admin.register(Chauffeur)
class ChauffeurAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_chauffeur', 'telephone', 'adresse', 'email', 'numero_voiture', 'societe', 'actif', 'super_chauffeur', 'has_mobile_password']  # <-- AJOUTEZ 'super_chauffeur' ICI
    
    search_fields = ['nom', 'telephone', 'numero_identite', 'adresse', 'email', 'numero_voiture']
    list_editable = ['actif', 'super_chauffeur']  # <-- AJOUTEZ 'super_chauffeur' ICI AUSSI
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('nom', 'type_chauffeur', 'telephone', 'actif', 'statut', 'super_chauffeur')  # <-- AJOUTEZ 'super_chauffeur' ICI
        }),
        ('Informations de contact', {
            'fields': ('adresse', 'email'),
            'description': "Pour l'interface mobile des chauffeurs"
        }),
        ('Véhicule', {
            'fields': ('numero_identite', 'numero_voiture', 'societe')
        }),
        ('Tarif', {
            'fields': ('prix_course_par_defaut',)
        }),
        ('Interface mobile', {
            'fields': ('mobile_password',),
            'description': 'Entrez un mot de passe simple (ex: 1234) - sera automatiquement hashé'
        }),
    )
    
    # AJOUTEZ AUSSI CE FILTRE SI VOUS VOULEZ
    list_filter = ['type_chauffeur', 'actif', 'super_chauffeur']  # <-- OPTIONNEL
    
    def has_mobile_password(self, obj):
        return bool(obj.mobile_password)
    has_mobile_password.boolean = True
    has_mobile_password.short_description = 'Mot de passe mobile'
@admin.register(HeureTransport)
class HeureTransportAdmin(admin.ModelAdmin):
    list_display = ['type_transport', 'heure', 'libelle', 'active', 'ordre']
    list_filter = ['type_transport', 'active']
    list_editable = ['active', 'ordre']
    ordering = ['type_transport', 'ordre']
from .models import NotificationAdmin

@admin.register(NotificationAdmin)
class NotificationAdminAdmin(admin.ModelAdmin):
    list_display = ['titre', 'type', 'date_creation', 'lu']
    list_filter = ['type', 'lu', 'date_creation']
    search_fields = ['titre', 'message']
    list_editable = ['lu']
    readonly_fields = ['date_creation']
    
    fieldsets = (
        ('Notification', {
            'fields': ('titre', 'message', 'type', 'lien')
        }),
        ('Statut', {
            'fields': ('lu', 'lu_par', 'date_lecture', 'date_creation')
        }),
    )
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['chauffeur', 'type_transport', 'heure', 'jour', 'date_reelle', 'prix_total', 'statut', 'get_nb_agents', 'demande_validation_at', 'validee_at']
    list_filter = ['type_transport', 'jour', 'chauffeur__type_chauffeur', 'date_reelle', 'statut']
    search_fields = ['chauffeur__nom', 'jour', 'notes_validation']
    list_editable = ['statut']
    readonly_fields = ['demande_validation_at', 'validee_at', 'created_at', 'get_point_depart']
    
    # ACTIONS POUR VALIDER/REFUSER
    actions = ['valider_courses', 'refuser_courses', 'marquer_payees']
    
    def valider_courses(self, request, queryset):
        for course in queryset:
            course.valider_par_admin("Validé via admin")
        self.message_user(request, f"{queryset.count()} courses validées avec succès")
    
    valider_courses.short_description = "✅ Valider les courses sélectionnées"
    
    def refuser_courses(self, request, queryset):
        for course in queryset:
            course.refuser_par_admin("Refusé via admin")
        self.message_user(request, f"{queryset.count()} courses refusées")
    
    refuser_courses.short_description = "❌ Refuser les courses sélectionnées"
    
    def marquer_payees(self, request, queryset):
        for course in queryset:
            if course.statut == 'validee':
                course.statut = 'payee'
                course.save()
        self.message_user(request, f"{queryset.count()} courses marquées comme payées")
    
    marquer_payees.short_description = "💰 Marquer comme payées"
    
    def get_nb_agents(self, obj):
        return obj.affectation_set.count()
    get_nb_agents.short_description = 'Nb Agents'
    
    def get_point_depart(self, obj):
        return "Complexe Zaoui" if obj.point_depart_adresse else "Non défini"
    get_point_depart.short_description = 'Point de départ'

    # Afficher les détails de validation
    fieldsets = (
        ('Informations de base', {
            'fields': ('chauffeur', 'type_transport', 'heure', 'jour', 'date_reelle')
        }),
        ('Finances', {
            'fields': ('prix_total', 'statut')
        }),
        ('Validation', {
            'fields': ('notes_validation', 'demande_validation_at', 'validee_at')
        }),
        ('Dates', {
            'fields': ('created_at',)
        }),
    )
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['chauffeur', 'agent', 'date_reservation', 'type_transport', 'get_heure_display', 'statut', 'created_at']
    list_filter = ['date_reservation', 'type_transport', 'statut', 'chauffeur']
    search_fields = ['chauffeur__nom', 'agent__nom', 'notes']
    list_editable = ['statut']
    date_hierarchy = 'date_reservation'
    
    fieldsets = (
        ('Réservation', {
            'fields': ('chauffeur', 'agent', 'date_reservation')
        }),
        ('Détails transport', {
            'fields': ('type_transport', 'heure_transport')
        }),
        ('Statut', {
            'fields': ('statut', 'notes')
        }),
    )
    
    def get_heure_display(self, obj):
        return obj.heure_display
    get_heure_display.short_description = 'Heure'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
       
        if db_field.name == "heure_transport":
            # On va filtrer dynamiquement via JavaScript dans le template
            pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['nom', 'get_societe_display', 'telephone', 'voiture_personnelle', 'est_complet', 'created_at']
    list_filter = ['societe', 'voiture_personnelle', 'created_at']
    search_fields = ['nom', 'adresse', 'telephone']
    list_editable = ['voiture_personnelle']
    
    def get_societe_display(self, obj):
        return obj.get_societe_display()
    get_societe_display.short_description = 'Société'
    
    def est_complet(self, obj):
        return obj.est_complet()
    est_complet.boolean = True
    est_complet.short_description = 'Infos complètes'
    
    actions = ['exporter_agents_excel', 'importer_agents_excel']
    
    def exporter_agents_excel(self, request, queryset):
        data = {
            'voyant': [],
            'adresse': [],
            'Mobile': [],
            'societe': [],
            'voiture': [],
        }
        
        for agent in queryset:
            data['voyant'].append(agent.nom)
            data['adresse'].append(agent.adresse)
            data['Mobile'].append(agent.telephone)
            data['societe'].append(agent.get_societe_display())
            data['voiture'].append('oui' if agent.voiture_personnelle else 'non')
        
        df = pd.DataFrame(data)
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="info_export.xlsx"'
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Agents', index=False)
        
        output.seek(0)
        response.write(output.getvalue())
        return response
    
    exporter_agents_excel.short_description = "Exporter les agents sélectionnés vers Excel"
    
    def importer_agents_excel(self, request, queryset):
        from django.shortcuts import render
        from .forms import ImportAgentForm
        
        if 'apply' in request.POST:
            form = ImportAgentForm(request.POST, request.FILES)
            if form.is_valid():
                fichier = request.FILES['fichier_excel']
                try:
                    df = pd.read_excel(fichier)
                    agents_crees = 0
                    agents_modifies = 0
                    
                    for index, row in df.iterrows():
                        nom = row.get('voyant', '')
                        if nom:
                            agent, created = Agent.objects.get_or_create(
                                nom=nom,
                                defaults={
                                    'adresse': row.get('adresse', ''),
                                    'telephone': str(row.get('Mobile', '')),
                                    'societe_texte': row.get('societe', ''),
                                    'voiture_personnelle': row.get('voiture', '').lower() in ['oui', 'yes', 'true', '1'],
                                }
                            )
                            
                            if created:
                                agents_crees += 1
                            else:
                                agent.adresse = row.get('adresse', agent.adresse)
                                agent.telephone = str(row.get('Mobile', agent.telephone))
                                agent.societe_texte = row.get('societe', agent.societe_texte)
                                agent.voiture_personnelle = row.get('voiture', '').lower() in ['oui', 'yes', 'true', '1']
                                agent.save()
                                agents_modifies += 1
                    
                    self.message_user(request, f"{agents_crees} agents créés, {agents_modifies} agents modifiés avec succès!")
                    return
                    
                except Exception as e:
                    self.message_user(request, f"Erreur lors de l'import: {str(e)}", level='error')
        
        else:
            form = ImportAgentForm()
        
        return render(request, 'admin/importer_agents.html', {'form': form, 'agents': queryset})
    
    importer_agents_excel.short_description = "Importer des agents depuis Excel"

@admin.register(Affectation)
class AffectationAdmin(admin.ModelAdmin):
    list_display = ['chauffeur', 'agent', 'societe_agent', 'adresse_agent', 'type_transport', 'heure', 'jour', 'date_reelle', 'prix_societe']
    list_filter = ['type_transport', 'jour', 'chauffeur__type_chauffeur', 'date_reelle']
    search_fields = ['chauffeur__nom', 'agent__nom', 'agent__societe__nom']
    
    def societe_agent(self, obj):
        return obj.agent.get_societe_display()
    societe_agent.short_description = 'Société'
    
    def adresse_agent(self, obj):
        return obj.agent.adresse
    adresse_agent.short_description = 'Adresse'
