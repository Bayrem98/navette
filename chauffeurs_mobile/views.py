# Vues API pour l'interface mobile
# VERSION COMPLÈTE AVEC TOUTES LES FONCTIONS

import json
from datetime import datetime, date, timedelta
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
import csv

try:
    # Essayer d'importer depuis votre structure d'app
    from django.apps import apps
    
    # Récupérer les modèles de manière dynamique
    Chauffeur = apps.get_model('gestion', 'Chauffeur')
    Course = apps.get_model('gestion', 'Course')
    Agent = apps.get_model('gestion', 'Agent')
    Affectation = apps.get_model('gestion', 'Affectation')
    Reservation = apps.get_model('gestion', 'Reservation')
    HeureTransport = apps.get_model('gestion', 'HeureTransport')
    
    MODELS_IMPORTED = True
    print("✅ Modèles importés via apps.get_model()")
except Exception as e:
    print(f"❌ Erreur import modèles: {e}")
    MODELS_IMPORTED = False

# ============================================
# FONCTIONS DE NOTIFICATION
# ============================================

def get_chauffeur_name(chauffeur_id):
    """Récupérer le nom d'un chauffeur par son ID"""
    try:
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        return chauffeur.nom
    except:
        return "Chauffeur inconnu"

def create_notification(chauffeur_id, type_notification, message, data=None):
    """Créer une notification pour un chauffeur"""
    try:
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        notification = MobileNotification.objects.create(
            chauffeur=chauffeur,
            type_notification=type_notification,
            message=message,
            data=data or {}
        )
        
        print(f"📢 Notification créée pour {chauffeur.nom}: {message}")
        return notification
        
    except Exception as e:
        print(f"❌ Erreur création notification: {e}")
        return None

def notify_super_reservation(chauffeur_cible_id, super_chauffeur_nom, agent_nom, heure_libelle, type_transport):
    """Notifier un chauffeur qu'un super chauffeur a réservé pour lui"""
    message = f"📅 {super_chauffeur_nom} a réservé l'agent {agent_nom} pour vous ({type_transport} - {heure_libelle})"
    
    return create_notification(
        chauffeur_id=chauffeur_cible_id,
        type_notification='super_reservation',
        message=message,
        data={
            'super_chauffeur': super_chauffeur_nom,
            'agent_nom': agent_nom,
            'heure_libelle': heure_libelle,
            'type_transport': type_transport,
            'action': 'reservation'
        }
    )

def notify_super_annulation(chauffeur_cible_id, super_chauffeur_nom, agent_nom, heure_libelle, type_transport):
    """Notifier un chauffeur qu'un super chauffeur a annulé sa réservation"""
    message = f"❌ {super_chauffeur_nom} a annulé votre réservation de {agent_nom} ({type_transport} - {heure_libelle})"
    
    return create_notification(
        chauffeur_id=chauffeur_cible_id,
        type_notification='super_annulation',
        message=message,
        data={
            'super_chauffeur': super_chauffeur_nom,
            'agent_nom': agent_nom,
            'heure_libelle': heure_libelle,
            'type_transport': type_transport,
            'action': 'annulation'
        }
    )

def notify_all_super_chauffeurs(type_action, chauffeur_responsable_id, agent_nom, heure_libelle, type_transport, agent_id=None):
    """
    Notifie tous les super-chauffeurs d'une action (réservation/annulation)
    """
    try:
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        
        chauffeur_responsable = Chauffeur.objects.get(id=chauffeur_responsable_id)
        
        # Vérifier si le chauffeur responsable est un super-chauffeur
        is_super_chauffeur = getattr(chauffeur_responsable, 'super_chauffeur', False)
        
        # Récupérer tous les super-chauffeurs actifs
        super_chauffeurs = Chauffeur.objects.filter(
            super_chauffeur=True, 
            actif=True
        )
        
        notifications_count = 0
        
        for super_chauffeur in super_chauffeurs:
            # Si c'est un super-chauffeur qui fait l'action, on ne se notifie pas soi-même
            if is_super_chauffeur and super_chauffeur.id == chauffeur_responsable_id:
                continue
                
            if type_action == 'reservation':
                if is_super_chauffeur:
                    # Un super-chauffeur réserve pour quelqu'un d'autre
                    message = f"👑 {chauffeur_responsable.nom} a réservé {agent_nom} ({type_transport} - {heure_libelle})"
                else:
                    # Un chauffeur normal réserve
                    message = f"📅 {chauffeur_responsable.nom} a réservé {agent_nom} ({type_transport} - {heure_libelle})"
                
                notification_type = 'super_reservation'
            else:  # annulation
                if is_super_chauffeur:
                    # Un super-chauffeur annule
                    message = f"👑 {chauffeur_responsable.nom} a annulé la réservation de {agent_nom} ({type_transport} - {heure_libelle})"
                else:
                    # Un chauffeur normal annule
                    message = f"❌ {chauffeur_responsable.nom} a annulé sa réservation de {agent_nom} ({type_transport} - {heure_libelle})"
                
                notification_type = 'super_annulation'
            
            MobileNotification.objects.create(
                chauffeur=super_chauffeur,
                type_notification=notification_type,
                message=message,
                data={
                    'chauffeur_responsable': chauffeur_responsable.nom,
                    'chauffeur_responsable_id': chauffeur_responsable_id,
                    'agent_nom': agent_nom,
                    'agent_id': agent_id,
                    'heure_libelle': heure_libelle,
                    'type_transport': type_transport,
                    'action': type_action,
                    'is_super_chauffeur_action': is_super_chauffeur
                }
            )
            
            notifications_count += 1
            print(f"📢 Notification envoyée à super-chauffeur: {super_chauffeur.nom}")
        
        print(f"✅ {notifications_count} notification(s) envoyée(s) aux super-chauffeurs")
        return notifications_count
        
    except Exception as e:
        print(f"❌ Erreur notification super-chauffeurs: {e}")
        import traceback
        traceback.print_exc()
        return 0
# ============================================
# NOTIFICATION POUR SUPER CHAUFFEUR
# ============================================
def notify_super_chauffeurs_hors_planning(course, agent, chauffeur):
    """
    Notifie tous les super-chauffeurs quand un agent hors planning est transporté
    """
    try:
        from django.apps import apps
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        
        # Récupérer tous les super-chauffeurs actifs
        super_chauffeurs = Chauffeur.objects.filter(
            super_chauffeur=True,
            actif=True
        )
        
        notifications_count = 0
        
        for super_chauffeur in super_chauffeurs:
            # Ne pas notifier le chauffeur qui a créé la course si c'est un super
            if super_chauffeur.id == chauffeur.id:
                continue
                
            notification = MobileNotification.objects.create(
                chauffeur=super_chauffeur,
                type_notification='alerte',
                message=f"🚨 Agent {agent.nom} transporté hors planning par {chauffeur.nom} à {course.heure}h",
                data={
                    'agent_nom': agent.nom,
                    'chauffeur_nom': chauffeur.nom,
                    'course_id': course.id,
                    'date': course.date_reelle.strftime('%d/%m/%Y'),
                    'heure': course.heure,
                    'type': 'hors_planning'
                },
                vue=False
            )
            notifications_count += 1
            print(f"📢 Notification envoyée à super-chauffeur: {super_chauffeur.nom}")
        
        print(f"✅ {notifications_count} notification(s) envoyée(s) aux super-chauffeurs")
        return notifications_count
        
    except Exception as e:
        print(f"❌ Erreur notification super-chauffeurs: {e}")
        return 0
def notify_reservation_confirmee(chauffeur_id, agent_nom, heure_libelle, type_transport):
    """Notifier un chauffeur que sa réservation est confirmée"""
    message = f"✅ Réservation confirmée: {agent_nom} ({type_transport} - {heure_libelle})"
    
    return create_notification(
        chauffeur_id=chauffeur_id,
        type_notification='reservation',
        message=message,
        data={
            'agent_nom': agent_nom,
            'heure_libelle': heure_libelle,
            'type_transport': type_transport,
            'action': 'confirmation'
        }
    )
def create_grouped_super_reservation_notification(chauffeur_cible_id, super_chauffeur_nom, agents, 
                                                  heure_transport, type_transport, is_multiple_reservation=True):
    """
    Créer une notification groupée pour un chauffeur quand un super-chauffeur
    réserve plusieurs agents pour lui
    """
    try:
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        
        chauffeur_cible = Chauffeur.objects.get(id=chauffeur_cible_id)
        
        if is_multiple_reservation and len(agents) > 1:
            # NOTIFICATION GROUPÉE
            agents_list = [agent.nom for agent in agents]
            agents_count = len(agents)
            
            message = f"👑 {super_chauffeur_nom} a réservé {agents_count} agent(s) pour vous"
            
            notification = MobileNotification.objects.create(
                chauffeur=chauffeur_cible,
                type_notification='super_reservation',
                message=message,
                data={
                    'super_chauffeur': super_chauffeur_nom,
                    'agents': agents_list,
                    'agents_count': agents_count,
                    'heure_libelle': heure_transport.libelle,
                    'type_transport': type_transport,
                    'action': 'reservation',
                    'is_grouped': True,
                    'date_transport': (datetime.now().date() + timedelta(days=1)).isoformat(),
                    'heure_transport_id': heure_transport.id,
                    'type_transport': type_transport,
                    'groupe_notification': f"{(date.today() + timedelta(days=1)).isoformat()}_{heure_transport.id}"
                },
                heure_transport=heure_transport,
                date_transport=(date.today() + timedelta(days=1)),
                type_transport=type_transport
            )
            
            print(f"📢 Notification groupée créée pour {chauffeur_cible.nom}: {agents_count} agent(s)")
            
        else:
            # Notification individuelle (pour compatibilité)
            for agent in agents:
                message = f"👑 {super_chauffeur_nom} a réservé l'agent {agent.nom} pour vous"
                
                MobileNotification.objects.create(
                    chauffeur=chauffeur_cible,
                    type_notification='super_reservation',
                    message=message,
                    data={
                        'super_chauffeur': super_chauffeur_nom,
                        'agent_nom': agent.nom,
                        'agent_id': agent.id,
                        'heure_libelle': heure_transport.libelle,
                        'type_transport': type_transport,
                        'action': 'reservation',
                        'is_grouped': False
                    }
                )
                
                print(f"📢 Notification individuelle créée pour {chauffeur_cible.nom}: {agent.nom}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur création notification groupée: {e}")
        return False

def create_self_reservation_notification(super_chauffeur, agents, heure_transport, type_transport):
    """
    Créer une notification pour un super-chauffeur qui se réserve des agents
    """
    try:
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        
        if len(agents) > 1:
            # Notification groupée
            agents_list = [agent.nom for agent in agents]
            agents_count = len(agents)
            
            message = f"✅ Vous avez réservé {agents_count} agent(s) pour vous-même"
            
            MobileNotification.objects.create(
                chauffeur=super_chauffeur,
                type_notification='reservation',
                message=message,
                data={
                    'agents': agents_list,
                    'agents_count': agents_count,
                    'heure_libelle': heure_transport.libelle,
                    'type_transport': type_transport,
                    'action': 'self_reservation',
                    'is_grouped': True
                }
            )
            
            print(f"📢 Notification groupée créée pour {super_chauffeur.nom}: {agents_count} agent(s) réservés")
            
        else:
            # Notification individuelle
            for agent in agents:
                message = f"✅ Vous avez réservé l'agent {agent.nom} pour vous-même"
                
                MobileNotification.objects.create(
                    chauffeur=super_chauffeur,
                    type_notification='reservation',
                    message=message,
                    data={
                        'agent_nom': agent.nom,
                        'heure_libelle': heure_transport.libelle,
                        'type_transport': type_transport,
                        'action': 'self_reservation',
                        'is_grouped': False
                    }
                )
                
                print(f"📢 Notification créée pour {super_chauffeur.nom}: {agent.nom} réservé")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur création notification self: {e}")
        return False
def notify_reservation_annulee(chauffeur_id, agent_nom, heure_libelle, type_transport, par_super=False, super_nom=None):
    """Notifier un chauffeur que sa réservation est annulée"""
    if par_super and super_nom:
        message = f"❌ {super_nom} a annulé votre réservation de {agent_nom}"
    else:
        message = f"❌ Votre réservation de {agent_nom} a été annulée"
    
    return create_notification(
        chauffeur_id=chauffeur_id,
        type_notification='annulation',
        message=message,
        data={
            'agent_nom': agent_nom,
            'heure_libelle': heure_libelle,
            'type_transport': type_transport,
            'par_super': par_super,
            'super_nom': super_nom if par_super else None
        }
    )
def create_grouped_notification(chauffeur_id, type_notification, message, data=None, 
                                heure_transport_id=None, date_transport=None, type_transport=''):
    """Créer une notification groupée par heure de transport"""
    try:
        from django.apps import apps
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        HeureTransport = apps.get_model('gestion', 'HeureTransport')
        
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        # Récupérer l'heure de transport si fournie
        heure_transport = None
        if heure_transport_id:
            heure_transport = HeureTransport.objects.get(id=heure_transport_id)
        
        # Créer la notification avec groupement
        notification = MobileNotification.objects.create(
            chauffeur=chauffeur,
            type_notification=type_notification,
            message=message,
            data=data or {},
            heure_transport=heure_transport,
            date_transport=date_transport,
            type_transport=type_transport
        )
        
        print(f"📢 Notification groupée créée pour {chauffeur.nom}: {message}")
        return notification
        
    except Exception as e:
        print(f"❌ Erreur création notification groupée: {e}")
        return None

def notify_agent_transport(chauffeur_id, agent_nom, agent_adresse, heure_libelle, 
                           type_transport, heure_transport_id, date_transport):
    """
    Notifier un chauffeur qu'il doit transporter un agent à une heure spécifique
    """
    message = f"👤 {agent_nom} - {agent_adresse}"
    
    data = {
        'agent_nom': agent_nom,
        'agent_adresse': agent_adresse,
        'heure_libelle': heure_libelle,
        'type_transport': type_transport,
        'action': 'transport',
        'heure_transport_id': heure_transport_id,
        'date_transport': date_transport.isoformat() if date_transport else None
    }
    
    return create_grouped_notification(
        chauffeur_id=chauffeur_id,
        type_notification='agent_selection',
        message=message,
        data=data,
        heure_transport_id=heure_transport_id,
        date_transport=date_transport,
        type_transport=type_transport
    )

# ============================================
# VUES D'INTERFACE WEB
# ============================================

def mobile_login_view(request):
    """Page de connexion"""
    return render(request, 'chauffeurs_mobile/login.html')

def mobile_dashboard_view(request):
    """Page dashboard"""
    return render(request, 'chauffeurs_mobile/dashboard.html')

def mobile_selection_view(request):
    """Page sélection agents"""
    return render(request, 'chauffeurs_mobile/selection.html')

def mobile_reservation_view(request):
    """Page web pour les réservations J+1"""
    return render(request, 'chauffeurs_mobile/reservation.html')

def mobile_historique_view(request):
    """Page historique"""
    return render(request, 'chauffeurs_mobile/Historique.html')

def mobile_profile_view(request):
    """Page profil"""
    return render(request, 'chauffeurs_mobile/profile.html')

def mobile_super_dashboard_view(request):
    """Page Super Dashboard"""
    return render(request, 'chauffeurs_mobile/super_dashboard.html')

def mobile_super_chauffeur_detail_view(request, chauffeur_id):
    """Page web pour voir le détail d'un chauffeur"""
    return render(request, 'chauffeurs_mobile/super_chauffeur_detail.html')

def mobile_notifications_view(request):
    """Page de notifications"""
    return render(request, 'chauffeurs_mobile/notifications.html')

def mobile_notifications_grouped_view(request):
    """Page web pour les notifications groupées"""
    return render(request, 'chauffeurs_mobile/notifications_grouped.html')

def force_logout_all_devices(chauffeur_id):
    """Force la déconnexion de tous les appareils d'un chauffeur"""
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        deleted_count = 0
        for session in Session.objects.filter(expire_date__gt=timezone.now()):
            session_data = session.get_decoded()
            if session_data.get('chauffeur_id') == chauffeur_id:
                session.delete()
                deleted_count += 1
        
        print(f"🚪 Déconnexion forcée: {deleted_count} session(s) fermée(s) pour chauffeur {chauffeur_id}")
        return deleted_count
        
    except Exception as e:
        print(f"⚠️ Erreur déconnexion forcée: {e}")
        return 0

def force_logout_chauffeur(chauffeur_id, current_session_key=None):
    """
    Force la déconnexion de tous les appareils d'un chauffeur
    Retourne le nombre de sessions supprimées
    """
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        deleted_count = 0
        
        # Récupérer toutes les sessions non expirées
        sessions = Session.objects.filter(expire_date__gt=timezone.now())
        
        for session in sessions:
            try:
                session_data = session.get_decoded()
                
                # Vérifier si c'est la session du chauffeur
                if session_data.get('chauffeur_id') == chauffeur_id:
                    
                    # Éviter de supprimer la session courante si spécifiée
                    if current_session_key and session.session_key == current_session_key:
                        print(f"  ⏭️ Session courante conservée: {session.session_key[:10]}...")
                        continue
                    
                    # Supprimer la session
                    session.delete()
                    deleted_count += 1
                    print(f"  🚪 Session supprimée: {session.session_key[:10]}...")
                    
            except Exception as e:
                print(f"  ⚠️ Erreur session {session.session_key[:10]}: {e}")
                continue
        
        print(f"✅ {deleted_count} session(s) supprimée(s) pour chauffeur {chauffeur_id}")
        return deleted_count
        
    except Exception as e:
        print(f"❌ Erreur déconnexion forcée: {e}")
        import traceback
        traceback.print_exc()
        return 0

# ============================================
# API ENDPOINTS
# ============================================
@csrf_exempt
@require_GET
def api_course_agents(request, course_id):
    """API pour récupérer les agents d'une course spécifique"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        # Vérifier si c'est un super-chauffeur
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        if not getattr(chauffeur, 'super_chauffeur', False):
            return JsonResponse({'success': False, 'error': 'Accès réservé'}, status=403)
        
        # Récupérer la course et ses affectations
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        course = Course.objects.get(id=course_id)
        affectations = Affectation.objects.filter(course=course).select_related('agent')
        
        agents_data = []
        for aff in affectations:
            if aff.agent:
                agent = aff.agent
                agents_data.append({
                    'id': agent.id,
                    'nom': agent.nom,
                    'adresse': agent.adresse or 'Non spécifiée',
                    'telephone': agent.telephone or 'Non spécifié',
                    'email': getattr(agent, 'email', ''),
                    'societe': agent.get_societe_display() if hasattr(agent, 'get_societe_display') else 'Non spécifiée',
                    'est_complet': agent.est_complet() if hasattr(agent, 'est_complet') else True
                })
        
        return JsonResponse({
            'success': True,
            'course_id': course_id,
            'agents': agents_data,
            'total': len(agents_data)
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Course non trouvée'}, status=404)
    except Exception as e:
        print(f"❌ Erreur api_course_agents: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
@csrf_exempt
@require_GET
def api_export_historique(request):
    """API pour exporter l'historique en CSV"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Récupérer toutes les courses du chauffeur
        courses = Course.objects.filter(chauffeur_id=chauffeur_id).order_by('-date_reelle', '-heure')
        
        # Créer la réponse CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="historique_courses_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response, delimiter=';')
        
        # En-têtes
        writer.writerow(['Date', 'Heure', 'Type', 'Statut', 'Nb Agents', 'Prix (DNT)', 'Notes'])
        
        # Données
        for course in courses:
            nb_agents = Affectation.objects.filter(course=course).count()
            prix = course.get_prix_course() if hasattr(course, 'get_prix_course') else 0
            
            writer.writerow([
                course.date_reelle.strftime('%d/%m/%Y'),
                f"{course.heure}h",
                'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                course.get_statut_display(),
                nb_agents,
                f"{float(prix):.2f}",
                course.notes_validation or ''
            ])
        
        return response
        
    except Exception as e:
        print(f"❌ Erreur export: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_GET
def api_profile(request):
    """API pour récupérer les données du profil - VERSION CORRIGÉE"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        # Récupérer les modèles
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Course = apps.get_model('gestion', 'Course')
        
        # Récupérer le chauffeur
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        print(f"👤 Profil demandé pour: {chauffeur.nom} (ID: {chauffeur_id})")
        
        # ========== VÉRIFICATION DES CHAMPS ==========
        print("🔍 Vérification des champs:")
        
        # Liste de tous les champs possibles
        champs_possibles = [
            'nom', 'telephone', 'numero_voiture', 'type_chauffeur',
            'actif', 'adresse', 'email', 'societe', 'numero_identite',
            'prix_course_par_defaut', 'statut', 'created_at', 'super_chauffeur'
        ]
        
        profile_data = {}
        
        for champ in champs_possibles:
            if hasattr(chauffeur, champ):
                valeur = getattr(chauffeur, champ)
                # Convertir les valeurs spéciales
                if champ == 'created_at' and valeur:
                    valeur = valeur.strftime('%d/%m/%Y')
                profile_data[champ] = valeur
                print(f"  ✅ {champ}: {valeur}")
            else:
                profile_data[champ] = ''
                print(f"  ⚠️ {champ}: NON DISPONIBLE")
        
        # Alias pour compatibilité
        profile_data['vehicule'] = profile_data.get('numero_voiture', '')
        # ============================================
        
        # Statistiques
        total_courses = Course.objects.filter(chauffeur_id=chauffeur_id).count()
        courses_validees = Course.objects.filter(chauffeur_id=chauffeur_id, statut='validee').count()
        
        # Calcul du revenu total
        courses = Course.objects.filter(chauffeur_id=chauffeur_id, statut='validee')
        revenu_total = 0
        for course in courses:
            try:
                if hasattr(course, 'prix_total') and course.prix_total:
                    prix = float(course.prix_total)
                elif hasattr(course, 'get_prix_course'):
                    prix = float(course.get_prix_course() or 0)
                else:
                    prix = 0
                revenu_total += prix
            except (ValueError, TypeError):
                continue
        
        return JsonResponse({
            'success': True,
            'profile': profile_data,
            'stats': {
                'total_courses': total_courses,
                'courses_validees': courses_validees,
                'revenu_total': round(revenu_total, 2),
                'moyenne_mensuelle': round(revenu_total / 12, 2) if revenu_total > 0 else 0,
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur profil: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def api_profile_update(request):
    """API pour mettre à jour le profil - VERSION COMPLÈTE"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        print(f"📝 Mise à jour profil pour chauffeur {chauffeur_id}")
        print(f"📦 Données reçues: {data}")
        
        # Récupérer le chauffeur
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        print(f"✅ Chauffeur trouvé: {chauffeur.nom}")
        
        # ========== TOUS LES CHAMPS POSSIBLES ==========
        # Mapping: champ_interface -> champ_modele
        champs_mapping = {
            'nom': 'nom',
            'telephone': 'telephone',
            'vehicule': 'numero_voiture',  # 'vehicule' dans l'interface = 'numero_voiture' en DB
            'adresse': 'adresse',
            'email': 'email',
            'societe': 'societe'
        }
        
        modifications = []
        
        for champ_interface, champ_modele in champs_mapping.items():
            if champ_interface in data and data[champ_interface] is not None:
                nouvelle_valeur = str(data[champ_interface]).strip()
                
                # Vérifier si le champ existe dans le modèle
                if hasattr(chauffeur, champ_modele):
                    ancienne_valeur = getattr(chauffeur, champ_modele, '') or ''
                    
                    if nouvelle_valeur != ancienne_valeur:
                        setattr(chauffeur, champ_modele, nouvelle_valeur)
                        modifications.append(champ_interface)
                        print(f"✅ {champ_interface} ({champ_modele}): '{ancienne_valeur}' -> '{nouvelle_valeur}'")
                else:
                    print(f"⚠️ Champ {champ_modele} n'existe pas dans le modèle")
        
        # Sauvegarder si modifications
        if modifications:
            chauffeur.save()
            print(f"💾 Profil sauvegardé: {len(modifications)} modification(s)")
            
            # Mettre à jour la session
            if 'nom' in modifications:
                request.session['chauffeur_nom'] = chauffeur.nom
                request.session.save()
            
            # Préparer réponse
            response_data = {
                'success': True,
                'message': f'Profil mis à jour ({len(modifications)} modification(s))',
                'modifications': modifications,
            }
            
            # Ajouter les données mises à jour
            updated_profile = {}
            for champ_interface, champ_modele in champs_mapping.items():
                if hasattr(chauffeur, champ_modele):
                    updated_profile[champ_interface] = getattr(chauffeur, champ_modele, '')
            
            response_data['profile'] = updated_profile
            
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'success': True,
                'message': 'Aucune modification nécessaire',
                'modifications': []
            })
        
    except Exception as e:
        print(f"❌ Erreur mise à jour profil: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }, status=500)

@csrf_exempt
@require_POST
def api_change_password(request):
    """API pour changer le mot de passe du chauffeur - VERSION CORRIGÉE"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        print(f"🔐 API changement mot de passe pour chauffeur {chauffeur_id}")
        print(f"📦 Données reçues: current='{current_password}', new='{new_password}', confirm='{confirm_password}'")
        
        # Validation des données
        if not current_password or not new_password or not confirm_password:
            return JsonResponse({
                'success': False,
                'error': 'Tous les champs sont requis'
            })
        
        if new_password != confirm_password:
            return JsonResponse({
                'success': False,
                'error': 'Les nouveaux mots de passe ne correspondent pas'
            })
        
        # Validation renforcée
        if len(new_password) < 8:
            return JsonResponse({
                'success': False, 
                'error': 'Le mot de passe doit faire au moins 8 caractères'
            })
        
        if not any(char.isdigit() for char in new_password):
            return JsonResponse({
                'success': False,
                'error': 'Le mot de passe doit contenir au moins un chiffre (0-9)'
            })
        
        if not any(char.isalpha() for char in new_password):
            return JsonResponse({
                'success': False,
                'error': 'Le mot de passe doit contenir au moins une lettre'
            })
        
        # Récupérer le chauffeur
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        
        try:
            chauffeur = Chauffeur.objects.get(id=chauffeur_id)
            print(f"✅ Chauffeur trouvé: {chauffeur.nom} (ID: {chauffeur.id})")
        except Chauffeur.DoesNotExist:
            print(f"❌ Chauffeur {chauffeur_id} non trouvé")
            return JsonResponse({
                'success': False,
                'error': 'Chauffeur non trouvé'
            }, status=404)
        
        # ========== VÉRIFICATION MOT DE PASSE ACTUEL ==========
        import hashlib
        current_hash = hashlib.sha256(current_password.encode()).hexdigest()
        
        print(f"🔑 Hash actuel calculé: {current_hash}")
        print(f"🔑 Hash stocké en DB: {chauffeur.mobile_password}")
        
        # Si pas de mot de passe défini (première fois)
        if not chauffeur.mobile_password:
            print(f"⚠️ Premier mot de passe pour {chauffeur.nom}")
            # On accepte n'importe quel mot de passe actuel pour la première configuration
            pass  # Continuer
        elif chauffeur.mobile_password != current_hash:
            print(f"❌ Hash ne correspond pas!")
            return JsonResponse({
                'success': False,
                'error': 'Mot de passe actuel incorrect'
            })
        # ======================================================
        
        # Vérifier que le nouveau est différent de l'ancien
        new_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        if chauffeur.mobile_password == new_hash:
            return JsonResponse({
                'success': False,
                'error': "Le nouveau mot de passe doit être différent de l'ancien"
            })
        
        # ========== CHANGEMENT DE MOT DE PASSE ==========
        print(f"💾 Sauvegarde nouveau mot de passe...")
        chauffeur.mobile_password = new_hash
        chauffeur.save()  # ICI, la méthode save() de votre modèle sera appelée
        print(f"✅ Mot de passe changé avec succès pour {chauffeur.nom}")
        # ===============================================
        
        # ========== DÉCONNEXION FORCÉE ==========
        print(f"🚪 Déconnexion forcée en cours...")
        
        # 1. Flusher la session courante IMMÉDIATEMENT
        request.session.flush()
        print("🧹 Session courante flushée")
        
        # 2. Supprimer TOUTES les sessions de la base de données
        try:
            from django.contrib.sessions.models import Session
            from django.utils import timezone
            
            sessions_deleted = 0
            active_sessions = Session.objects.filter(expire_date__gt=timezone.now())
            
            for session in active_sessions:
                try:
                    session_data = session.get_decoded()
                    if session_data.get('chauffeur_id') == chauffeur_id:
                        session.delete()
                        sessions_deleted += 1
                except Exception as e:
                    print(f"  ⚠️ Erreur session: {e}")
                    continue
            
            print(f"🗑️  {sessions_deleted} session(s) supprimée(s) de la DB")
            
        except Exception as e:
            print(f"⚠️ Erreur suppression sessions DB: {e}")
        # ========================================
        
        return JsonResponse({
            'success': True,
            'message': 'Mot de passe changé avec succès. Vous avez été déconnecté.',
            'redirect_to_login': True,
            'logout_forced': True
        })
        
    except Exception as e:
        print(f"❌ ERREUR FATALE dans api_change_password: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }, status=500)

@csrf_exempt
@require_POST
def api_login(request):
    """Connexion avec vérification du mot de passe"""
    try:
        data = json.loads(request.body)
        telephone = data.get('telephone', '').strip()
        password = data.get('password', '')
        
        if not telephone or not password:
            return JsonResponse({'success': False, 'message': 'Téléphone et mot de passe requis'})
        
        # Récupérer le modèle Chauffeur
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        
        # Chercher le chauffeur
        chauffeur = Chauffeur.objects.filter(
            telephone=telephone,
            actif=True
        ).first()
        
        if not chauffeur:
            return JsonResponse({'success': False, 'message': 'Chauffeur non trouvé ou inactif'})
        
        # Vérifier le mot de passe
        if hasattr(chauffeur, 'mobile_password') and chauffeur.mobile_password:
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if chauffeur.mobile_password != password_hash:
                return JsonResponse({'success': False, 'message': 'Mot de passe incorrect'})
        
        # ===== CRUCIAL : Utiliser le nom de cookie spécifique =====
        # Stocker les données dans la session
        request.session['chauffeur_id'] = chauffeur.id
        request.session['chauffeur_nom'] = chauffeur.nom
        request.session['telephone'] = telephone
        
        # Marquer comme session mobile
        request.session['is_mobile_session'] = True
        
        request.session.save()
        
        # Configurer la réponse avec le bon cookie
        response = JsonResponse({
            'success': True,
            'message': 'Connecté avec succès',
            'chauffeur': {
                'id': chauffeur.id,
                'nom': chauffeur.nom,
                'telephone': chauffeur.telephone,
                'type_chauffeur': getattr(chauffeur, 'type_chauffeur', 'taxi'),
                'super_chauffeur': getattr(chauffeur, 'super_chauffeur', False)
            }
        })
        
        # IMPORTANT : S'assurer que le cookie mobile est bien défini
        from django.conf import settings
        response.set_cookie(
            settings.MOBILE_SESSION_COOKIE_NAME,
            request.session.session_key,
            max_age=settings.MOBILE_SESSION_COOKIE_AGE,
            path=settings.MOBILE_SESSION_COOKIE_PATH,
            secure=settings.MOBILE_SESSION_COOKIE_SECURE,
            httponly=settings.MOBILE_SESSION_COOKIE_HTTPONLY,
            samesite=settings.MOBILE_SESSION_COOKIE_SAMESITE
        )
        
        return response
            
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return JsonResponse({'success': False, 'message': f'Erreur: {str(e)}'})
# API de déconnexion
@csrf_exempt
@require_POST
def api_logout(request):
    """API de déconnexion - NE SUPPRIME QUE LA SESSION MOBILE"""
    
    # Sauvegarder les clés admin avant de flusher
    admin_keys = {}
    for key in list(request.session.keys()):
        # Ne pas sauvegarder les clés mobile
        if not key.startswith('chauffeur_') and key != 'is_mobile_session':
            admin_keys[key] = request.session[key]
            print(f"🔐 Préservation de la clé admin: {key}")
    
    # Flusher la session (supprime tout)
    request.session.flush()
    
    # RESTAURER les clés admin
    for key, value in admin_keys.items():
        request.session[key] = value
        print(f"✅ Clé admin restaurée: {key}")
    
    request.session.save()
    
    return JsonResponse({'success': True, 'message': 'Déconnecté (session mobile uniquement)'})
# API dashboard
@csrf_exempt
@require_GET
def api_dashboard(request):
    """API dashboard - Courses d'aujourd'hui seulement"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        print(f"❌ Pas de chauffeur_id dans la session")
        return JsonResponse({
            'success': False,
            'message': 'Session expirée',
            'redirect': '/mobile/login/'
        }, status=401)
    
    try:
        # Récupérer les modèles
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Récupérer le chauffeur
        try:
            chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        except Chauffeur.DoesNotExist:
            print(f"❌ Chauffeur {chauffeur_id} non trouvé en DB")
            # Nettoyer la session
            request.session.flush()
            return JsonResponse({
                'success': False,
                'message': 'Chauffeur non trouvé',
                'redirect': '/mobile/login/'
            }, status=401)
        
        is_super_chauffeur = getattr(chauffeur, 'super_chauffeur', False)
        
        # Date d'aujourd'hui
        aujourd_hui = timezone.now().date()
        
        print(f"📊 Dashboard pour chauffeur {chauffeur_id} - Date: {aujourd_hui}")        
        # 1. Courses d'aujourd'hui (tous statuts)
        courses_aujourdhui = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            date_reelle=aujourd_hui
        ).order_by('heure')
        
        print(f"📅 Courses aujourd'hui: {courses_aujourdhui.count()}")
        
        # 2. Courses VALIDÉES (toutes dates)
        courses_validees = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            statut__in=['validee', 'payee']
        )
        
        print(f"✅ Courses validées: {courses_validees.count()}")
        
        # 3. Courses EN ATTENTE (aujourd'hui)
        courses_attente = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            date_reelle=aujourd_hui,
            statut='en_attente'
        )
        
        print(f"⏳ Courses en attente: {courses_attente.count()}")
        
        # 4. Courses ANNULÉES (aujourd'hui)
        courses_annulees = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            date_reelle=aujourd_hui,
            statut='annulee'
        )
        
        print(f"❌ Courses annulées: {courses_annulees.count()}")
        
        # 5. Calculer le revenu des courses validées
        revenu_total = 0
        for course in courses_validees:
            try:
                # Essayer différentes façons de récupérer le prix
                if hasattr(course, 'prix_total') and course.prix_total:
                    prix = float(course.prix_total)
                elif hasattr(course, 'get_prix_course'):
                    prix = float(course.get_prix_course() or 0)
                elif hasattr(course, 'prix_course') and course.prix_course:
                    prix = float(course.prix_course)
                else:
                    prix = 0
                
                revenu_total += prix
                print(f"💰 Course {course.id} - Prix: {prix} DNT")
            except (ValueError, TypeError, AttributeError) as e:
                print(f"⚠️ Erreur prix course {course.id}: {e}")
                continue
        
        print(f"💰 Revenu total validé: {revenu_total} DNT")
        
        # 6. Préparer les données du dashboard
        courses_data = []
        for course in courses_aujourdhui:
            nb_agents = Affectation.objects.filter(course=course).count()
            
            # Déterminer le texte du statut
            statut_display = course.statut
            if hasattr(course, 'get_statut_display'):
                statut_display = course.get_statut_display()
            
            courses_data.append({
                'id': course.id,
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure:02d}:00",
                'nb_agents': nb_agents,
                'statut': course.statut,
                'statut_display': statut_display,
                'date': course.date_reelle.strftime('%d/%m/%Y'),
                'prix': float(course.get_prix_course() or 0) if hasattr(course, 'get_prix_course') else 0,
            })
        
        # 7. Construire la réponse
        response_data = {
            'success': True,
            'chauffeur': {
                'id': chauffeur.id,
                'nom': chauffeur.nom,
                'telephone': chauffeur.telephone,
                'vehicule': getattr(chauffeur, 'numero_voiture', 'Non spécifié'),
                'type_chauffeur': getattr(chauffeur, 'type_chauffeur', 'taxi'),
                'actif': chauffeur.actif,
                'super_chauffeur': is_super_chauffeur,
            },            
            'dashboard': {
                'date': aujourd_hui.strftime('%d/%m/%Y'),
                'heure_actuelle': timezone.now().strftime('%H:%M'),
                'stats': {
                    'total_courses': courses_aujourdhui.count(),
                    'courses_validees': courses_validees.count(),
                    'courses_attente': courses_attente.count(),
                    'courses_annulees': courses_annulees.count(),
                    'revenu_valide': round(revenu_total, 2) if is_super_chauffeur else 0,
                    'revenu_valide_display': f"{round(revenu_total, 2):.2f} DNT" if is_super_chauffeur else "Non disponible",
                },
                'courses_aujourdhui': courses_data
            }
        }
        
        # Debug: afficher la réponse
        print(f"📤 Réponse dashboard: {json.dumps(response_data, indent=2, default=str)}")
        
        return JsonResponse(response_data)
        
    except Chauffeur.DoesNotExist:
        print(f"❌ Chauffeur {chauffeur_id} non trouvé")
        return JsonResponse({
            'success': False,
            'message': 'Chauffeur non trouvé'
        }, status=404)
        
    except Exception as e:
        print(f"❌ ERREUR api_dashboard: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Erreur serveur: {str(e)}'
        }, status=500)

@csrf_exempt
@require_GET
def api_reservations_demain(request):
    """API pour voir les réservations de demain"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date, timedelta
        
        print(f"📅 API réservations demain appelée pour chauffeur {chauffeur_id}")
        
        # Récupérer les modèles AVEC GESTION D'ERREUR
        try:
            from django.apps import apps
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
            Reservation = apps.get_model('gestion', 'Reservation')
            HeureTransport = apps.get_model('gestion', 'HeureTransport')
            print("✅ Modèles importés avec succès")
        except Exception as e:
            print(f"❌ Erreur import modèles: {e}")
            # Fallback : utiliser des imports directs
            try:
                from gestion.models import Chauffeur, Reservation, HeureTransport
                print("✅ Modèles importés directement")
            except Exception as e2:
                print(f"❌ Erreur import direct: {e2}")
                return JsonResponse({
                    'success': False, 
                    'error': f'Erreur import modèles: {e2}',
                    'details': 'Vérifiez que les modèles existent dans gestion/models.py'
                })
        
        demain = date.today() + timedelta(days=1)
        print(f"📅 Date de demain: {demain}")
        
        # Récupérer le chauffeur
        try:
            chauffeur = Chauffeur.objects.get(id=chauffeur_id)
            print(f"👤 Chauffeur trouvé: {chauffeur.nom}")
        except Chauffeur.DoesNotExist:
            print(f"❌ Chauffeur {chauffeur_id} non trouvé")
            return JsonResponse({
                'success': False,
                'error': 'Chauffeur non trouvé'
            })
        
        # Récupérer les réservations existantes pour demain
        reservations_demain = Reservation.objects.filter(
            date_reservation=demain
        ).select_related('agent', 'heure_transport')
        
        print(f"📋 {reservations_demain.count()} réservation(s) trouvée(s) pour demain")
        
        # Récupérer les heures dynamiques configurées
        heures_ramassage = HeureTransport.objects.filter(
            type_transport='ramassage',
            active=True
        ).order_by('ordre')
        
        heures_depart = HeureTransport.objects.filter(
            type_transport='depart', 
            active=True
        ).order_by('ordre')
        
        print(f"⏰ {heures_ramassage.count()} heure(s) ramassage, {heures_depart.count()} heure(s) départ")
        
        # Préparer la réponse
        response_data = {
            'success': True,
            'date_demain': demain.strftime('%Y-%m-%d'),
            'date_demain_display': demain.strftime('%d/%m/%Y'),
            'chauffeur': {
                'id': chauffeur.id,
                'nom': chauffeur.nom,
            },
            'heures_ramassage': [
                {'id': h.id, 'heure': h.heure, 'libelle': h.libelle}
                for h in heures_ramassage
            ],
            'heures_depart': [
                {'id': h.id, 'heure': h.heure, 'libelle': h.libelle}
                for h in heures_depart
            ],
            'reservations_existantes': [
                {
                    'id': r.id,
                    'agent_id': r.agent.id,
                    'agent_nom': r.agent.nom,
                    'chauffeur_id': r.chauffeur.id,
                    'chauffeur_nom': r.chauffeur.nom,
                    'type_transport': r.type_transport,
                    'heure_id': r.heure_transport.id,
                    'heure_libelle': r.heure_transport.libelle,
                    'statut': r.statut,
                    'est_mienne': r.chauffeur.id == chauffeur_id
                }
                for r in reservations_demain
            ]
        }
        
        print(f"📤 Envoi réponse: {len(str(response_data))} bytes")
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"❌ Erreur api_reservations_demain: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@csrf_exempt
@require_POST
def api_reserver_agent(request):
    """API pour réserver un agent - VERSION AVEC NOTIFICATIONS SUPÉRIEURES"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        agent_id = data.get('agent_id')
        type_transport = data.get('type_transport')
        heure_id = data.get('heure_id')
        notes = data.get('notes', '')
        
        if not all([agent_id, type_transport, heure_id]):
            return JsonResponse({'success': False, 'error': 'Données manquantes'})
        
        from datetime import date, timedelta
        
        # Récupérer les modèles
        try:
            Reservation = apps.get_model('gestion', 'Reservation')
            Agent = apps.get_model('gestion', 'Agent')
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
            HeureTransport = apps.get_model('gestion', 'HeureTransport')
        except Exception as e:
            print(f"❌ Erreur import modèles: {e}")
            return JsonResponse({
                'success': False, 
                'error': 'Configuration incomplète'
            })
        
        demain = date.today() + timedelta(days=1)
        
        # ========== VÉRIFICATION CRITIQUE - DATE CORRECTE ==========
        # 1. Récupérer l'agent
        try:
            agent = Agent.objects.get(id=agent_id)
            print(f"👤 Agent trouvé: {agent.nom}")
        except Agent.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Agent non trouvé'})
        
        # 2. Vérifier si l'agent est programmé pour demain avec les VRAIES dates du planning
        # Convertir demain en jour de semaine
        jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        jour_semaine = jours_fr[demain.weekday()]
        
        # 3. Charger le planning EMS.xlsx
        try:
            from gestion.utils import GestionnaireTransport
            
            gestionnaire = GestionnaireTransport()
            
            # Recharger le planning depuis la session
            if not gestionnaire.recharger_planning_depuis_session():
                print("⚠️ Planning non chargé dans la session")
                return JsonResponse({
                    'success': False,
                    'error': "Planning non chargé. Veuillez d'abord charger le planning EMS.xlsx"
                })
            
            # 4. VÉRIFICATION CRITIQUE : Comparer les DATES RÉELLES, pas seulement les jours
            
            # Récupérer les dates extraites du planning
            dates_par_jour = gestionnaire.dates_par_jour
            print(f"📅 Dates extraites du planning: {dates_par_jour}")
            
            # Vérifier si la date de demain existe dans le planning
            date_demain_str = demain.strftime("%d/%m/%Y")
            jour_correspondant = None
            
            # Chercher quel jour dans le planning correspond à demain
            for jour_planning, date_planning_str in dates_par_jour.items():
                if date_planning_str == date_demain_str:
                    jour_correspondant = jour_planning
                    print(f"✅ Date trouvée dans planning: {date_demain_str} -> {jour_correspondant}")
                    break
            
            if not jour_correspondant:
                # Essayer de parser les dates pour comparer
                print("⚠️ Date exacte non trouvée, tentative de parsing...")
                for jour_planning, date_planning_str in dates_par_jour.items():
                    try:
                        # Essayer de parser la date du planning
                        date_planning = datetime.strptime(date_planning_str, "%d/%m/%Y").date()
                        if date_planning == demain:
                            jour_correspondant = jour_planning
                            print(f"✅ Date correspondante trouvée: {date_planning} -> {jour_correspondant}")
                            break
                    except:
                        continue
            
            if not jour_correspondant:
                print(f"❌ Aucune date dans le planning ne correspond à demain ({date_demain_str})")
                return JsonResponse({
                    'success': False,
                    'error': f'Le planning chargé ne contient pas la date du {date_demain_str}. Veuillez charger un planning actualisé.'
                })
            
            # 5. Vérifier le type de transport et l'heure
            heure_transport = HeureTransport.objects.get(id=heure_id)
            heure_valeur = heure_transport.heure
            
            print(f"🔍 Vérification: Agent {agent.nom}, {jour_correspondant} ({date_demain_str}), {type_transport}, {heure_valeur}h")
            
            # Simuler une recherche dans le planning pour le JOUR CORRECT
            class FiltreFormPlanning:
                def __init__(self, jour, type_transport, heure_valeur):
                    self.cleaned_data = {
                        'jour': jour,
                        'type_transport': type_transport,
                        'heure_ete': False,
                        'filtre_agents': 'tous'
                    }
                    self.data = {'heure_specifique': str(heure_valeur)}
            
            form_filtre = FiltreFormPlanning(jour_correspondant, type_transport, heure_valeur)
            liste_transports = gestionnaire.traiter_donnees(form_filtre)
            
            # Vérifier si l'agent est dans la liste filtrée
            agent_programme = False
            for transport in liste_transports:
                if transport.get('agent') == agent.nom:
                    agent_programme = True
                    print(f"✅ Agent {agent.nom} programmé pour {jour_correspondant} ({date_demain_str}) {type_transport} à {heure_valeur}h")
                    break
            
            if not agent_programme:
                # Afficher les agents disponibles pour aider au debug
                agents_disponibles = [t.get('agent') for t in liste_transports]
                print(f"❌ Agent {agent.nom} NON PROGRAMMÉ pour {jour_correspondant} ({date_demain_str}) {type_transport} à {heure_valeur}h")
                print(f"📋 Agents programmés à cette heure: {agents_disponibles}")
                
                return JsonResponse({
                    'success': False,
                    'error': f'Agent {agent.nom} non programmé pour {type_transport} à {heure_valeur}h le {date_demain_str}'
                })
            
        except Exception as e:
            print(f"⚠️ Erreur vérification planning: {e}")
            import traceback
            traceback.print_exc()
            # On continue quand même, mais c'est un risque            # On continue quand même, mais c'est un risque
        # ======================================================
        
        # Récupérer le chauffeur
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        heure_transport = HeureTransport.objects.get(id=heure_id)
        
        # **SOLUTION CRITIQUE** : Vérifier TOUTES les réservations, sans filtrer par statut
        reservation_existante = Reservation.objects.filter(
            agent_id=agent_id,
            date_reservation=demain,
            heure_transport_id=heure_id,
            type_transport=type_transport
        ).first()
        
        print(f"🔍 Réservation existante recherchée pour agent {agent_id}, date {demain}, heure {heure_id}, type {type_transport}")
        print(f"   Trouvée: {reservation_existante is not None}")
        
        if reservation_existante:
            print(f"   Détails: ID {reservation_existante.id}, Statut: {reservation_existante.statut}, Chauffeur: {reservation_existante.chauffeur.nom if reservation_existante.chauffeur else 'None'}")
            
            if reservation_existante.statut == 'annulee':
                # **CAS 1** : Réservation annulée - On peut la réactiver
                reservation_existante.chauffeur_id = chauffeur_id
                reservation_existante.statut = 'reservee'
                reservation_existante.notes = notes
                reservation_existante.updated_at = timezone.now()
                reservation_existante.save()
                
                print(f"✅ Réservation annulée réactivée: ID {reservation_existante.id}")
                
                # NOTIFICATION : Notifier les super-chauffeurs
                notify_all_super_chauffeurs(
                    type_action='reservation',
                    chauffeur_responsable_id=chauffeur_id,
                    agent_nom=agent.nom,
                    heure_libelle=heure_transport.libelle,
                    type_transport=type_transport,
                    agent_id=agent_id
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Réservation effectuée avec succès',
                    'reservation_id': reservation_existante.id,
                    'reactivated': True
                })
                
            elif reservation_existante.statut in ['reservee', 'confirmee']:
                # **CAS 2** : Réservation active
                if reservation_existante.chauffeur_id == int(chauffeur_id):
                    return JsonResponse({
                        'success': False,
                        'error': 'Vous avez déjà réservé cet agent'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Déjà réservé par le chauffeur {reservation_existante.chauffeur.nom}',
                        'chauffeur_reservant': reservation_existante.chauffeur.nom
                    })
            else:
                # **CAS 3** : Autre statut inattendu
                print(f"⚠️ Statut inattendu: {reservation_existante.statut}")
                return JsonResponse({
                    'success': False,
                    'error': f'Réservation existante avec statut inattendu: {reservation_existante.statut}'
                })
        
        # **CAS 4** : Pas de réservation existante - Créer une nouvelle
        try:
            reservation = Reservation.objects.create(
                chauffeur_id=chauffeur_id,
                agent_id=agent_id,
                date_reservation=demain,
                type_transport=type_transport,
                heure_transport_id=heure_id,
                notes=notes,
                statut='reservee'
            )
            
            print(f"✅ Nouvelle réservation créée: ID {reservation.id}")
            
            # NOTIFICATION IMPORTANTE : Notifier tous les super-chauffeurs
            notifications_sent = notify_all_super_chauffeurs(
                type_action='reservation',
                chauffeur_responsable_id=chauffeur_id,
                agent_nom=agent.nom,
                heure_libelle=heure_transport.libelle,
                type_transport=type_transport,
                agent_id=agent_id
            )
            
            print(f"📢 {notifications_sent} notification(s) envoyée(s) aux super-chauffeurs")
            
            return JsonResponse({
                'success': True,
                'message': 'Réservation effectuée avec succès',
                'reservation_id': reservation.id,
                'reactivated': False,
                'notifications_sent': notifications_sent
            })
            
        except Exception as e:
            # **CAS 5** : Erreur de contrainte UNIQUE (devrait être capturée plus tôt)
            print(f"❌ Erreur création: {e}")
            
            # Dernière tentative : rechercher à nouveau
            reservation_cachee = Reservation.objects.filter(
                agent_id=agent_id,
                date_reservation=demain,
                heure_transport_id=heure_id,
                type_transport=type_transport
            ).first()
            
            if reservation_cachee:
                return JsonResponse({
                    'success': False,
                    'error': f'Réservation cachée trouvée! Statut: {reservation_cachee.statut}, Chauffeur: {reservation_cachee.chauffeur.nom}'
                })
            
            return JsonResponse({
                'success': False, 
                'error': f'Erreur inconnue: {str(e)}'
            })
        
    except Exception as e:
        print(f"❌ Erreur api_reserver_agent: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_GET
def api_mes_reservations(request):
    """API pour voir les réservations du chauffeur"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date, timedelta
        
        try:
            Reservation = apps.get_model('gestion', 'Reservation')
        except:
            # Fallback si le modèle n'existe pas
            return JsonResponse({
                'success': False,
                'error': 'Module de réservation non disponible'
            })
        
        # Récupérer toutes les réservations du chauffeur
        reservations = Reservation.objects.filter(
            chauffeur_id=chauffeur_id
        ).select_related('agent', 'heure_transport').order_by('-date_reservation', 'heure_transport__heure')
        
        # Filtrer par date si fourni
        date_filter = request.GET.get('date')
        if date_filter:
            try:
                filter_date = date.fromisoformat(date_filter)
                reservations = reservations.filter(date_reservation=filter_date)
            except:
                pass
        
        # Préparer les données
        reservations_data = []
        for r in reservations:
            # Vérifier si peut être modifiée (pour aujourd'hui ou futur)
            peut_annuler = r.date_reservation > date.today()
            
            # Vérifier si c'est pour demain
            est_pour_demain = r.date_reservation == date.today() + timedelta(days=1)
            
            reservations_data.append({
                'id': r.id,
                'agent': {
                    'id': r.agent.id,
                    'nom': r.agent.nom,
                    'adresse': r.agent.adresse,
                    'telephone': r.agent.telephone,
                    'societe': r.agent.get_societe_display(),
                },
                'date': r.date_reservation.strftime('%Y-%m-%d'),
                'date_display': r.date_reservation.strftime('%d/%m/%Y'),
                'type_transport': r.type_transport,
                'type_display': 'Ramassage' if r.type_transport == 'ramassage' else 'Départ',
                'heure': {
                    'id': r.heure_transport.id,
                    'valeur': r.heure_transport.heure,
                    'libelle': r.heure_transport.libelle,
                },
                'statut': r.statut,
                'statut_display': r.get_statut_display(),
                'notes': r.notes or '',
                'created_at': r.created_at.strftime('%d/%m/%Y %H:%M'),
                'peut_annuler': peut_annuler,  # Logique calculée ici
                'est_pour_demain': est_pour_demain,  # Logique calculée ici
            })
        
        return JsonResponse({
            'success': True,
            'reservations': reservations_data,
            'total': len(reservations_data),
            'reservations_demain': len([r for r in reservations_data if r['est_pour_demain']]),
        })
        
    except Exception as e:
        print(f"❌ Erreur api_mes_reservations: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def api_annuler_reservation(request, reservation_id):
    """API pour annuler une réservation - VERSION AVEC NOTIFICATION SUPÉRIEURE"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date
        
        # Récupérer les modèles
        try:
            Reservation = apps.get_model('gestion', 'Reservation')
            MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
        except:
            return JsonResponse({
                'success': False, 
                'error': 'Module de réservation non disponible'
            })
        
        # Récupérer la réservation
        reservation = Reservation.objects.get(id=reservation_id, chauffeur_id=chauffeur_id)
        
        # Récupérer le chauffeur
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        # Vérifier si on peut annuler (date future)
        if reservation.date_reservation <= date.today():
            return JsonResponse({
                'success': False, 
                'error': 'Cette réservation ne peut plus être annulée (date passée)'
            })
        
        # NOTIFICATION IMPORTANTE : Notifier tous les super-chauffeurs
        notifications_sent = notify_all_super_chauffeurs(
            type_action='annulation',
            chauffeur_responsable_id=chauffeur_id,
            agent_nom=reservation.agent.nom,
            heure_libelle=reservation.heure_transport.libelle,
            type_transport=reservation.type_transport,
            agent_id=reservation.agent.id
        )
        
        print(f"📢 {notifications_sent} notification(s) d'annulation envoyée(s) aux super-chauffeurs")
        
        # Créer une notification pour le chauffeur lui-même (optionnel)
        try:
            MobileNotification.objects.create(
                chauffeur=reservation.chauffeur,
                type_notification='info',
                message=f"Réservation annulée - Agent: {reservation.agent.nom} ({reservation.get_type_transport_display()})",
                vue=False
            )
        except:
            pass  # Ne pas bloquer si la notification échoue
        
        # Annuler la réservation
        reservation.statut = 'annulee'
        reservation.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Réservation annulée avec succès',
            'reservation_id': reservation.id,
            'agent_id': reservation.agent.id,
            'agent_nom': reservation.agent.nom,
            'refresh_required': True,  # Indique au front de rafraîchir
            'notifications_sent': notifications_sent
        })
        
    except Reservation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Réservation non trouvée'})
    except Exception as e:
        print(f"❌ Erreur api_annuler_reservation: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_GET
def api_agents_disponibles_demain(request):
    
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date, timedelta
        
        # Récupérer les paramètres
        demain = date.today() + timedelta(days=1)
        type_transport = request.GET.get('type_transport', 'ramassage')
        heure_id = request.GET.get('heure_id')
        
        if not heure_id:
            return JsonResponse({'success': False, 'error': 'Heure non spécifiée'})
        
        # Récupérer les modèles
        try:
            from django.apps import apps
            Agent = apps.get_model('gestion', 'Agent')
            Reservation = apps.get_model('gestion', 'Reservation')
            HeureTransport = apps.get_model('gestion', 'HeureTransport')
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
        except Exception as e:
            print(f"❌ Erreur import modèles: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Configuration incomplète'
            })
        
        # 1. Récupérer l'heure de transport
        heure_transport = HeureTransport.objects.get(id=heure_id, active=True)
        heure_valeur = heure_transport.heure
        
        print(f"🔍 Recherche agents PROGRAMMÉS pour {type_transport} à {heure_valeur}h")
        
        # 2. Récupérer TOUTES les réservations pour demain à cette heure
        reservations_demain = Reservation.objects.filter(
            date_reservation=demain,
            heure_transport=heure_transport,
            type_transport=type_transport,
            statut__in=['reservee', 'confirmee']
        ).select_related('chauffeur', 'agent')
        
        print(f"📌 {reservations_demain.count()} réservation(s) trouvée(s)")
        
        # INITIALISER reservations_dict ICI, avant de l'utiliser
        reservations_dict = {}
        chauffeurs_reservants = {}  # Pour stocker qui a réservé
        
        for reservation in reservations_demain:
            reservations_dict[reservation.agent_id] = {
                'reserved': True,
                'chauffeur_id': reservation.chauffeur_id,
                'chauffeur_nom': reservation.chauffeur.nom,
                'reservation_id': reservation.id,
                'est_mienne': reservation.chauffeur_id == int(chauffeur_id)
            }
            chauffeurs_reservants[reservation.agent_id] = reservation.chauffeur.nom
        
        # 3. IMPORTANT : CHARGER LE PLANNING POUR FILTRER
        # Convertir demain en jour de semaine
        jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        jour_semaine = jours_fr[demain.weekday()]
        
        print(f"📅 Demain: {demain} -> {jour_semaine}")
        
        # 4. Charger le planning (comme dans votre vue liste_transports)
        try:
            from gestion.utils import GestionnaireTransport
            
            gestionnaire = GestionnaireTransport()
            
            # Essayer de charger le planning depuis la session
            if not gestionnaire.recharger_planning_depuis_session():
                print("⚠️ Planning non chargé dans la session")
                # Retourner une liste vide ou des agents de test
                return JsonResponse({
                    'success': True,
                    'date': demain.strftime('%Y-%m-%d'),
                    'date_display': demain.strftime('%d/%m/%Y'),
                    'type_transport': type_transport,
                    'heure': {
                        'id': heure_transport.id,
                        'libelle': heure_transport.libelle,
                        'valeur': heure_transport.heure,
                    },
                    'agents': [],
                    'total_agents': 0,
                    'total_disponibles': 0,
                    'total_reserves': 0,
                    'message': "Planning non chargé. Veuillez d'abord charger le planning EMS.xlsx"
                })
            
            # VÉRIFICATION CRITIQUE : Vérifier que la date de demain est dans le planning
            dates_par_jour = gestionnaire.dates_par_jour
            date_demain_str = demain.strftime("%d/%m/%Y")
            
            jour_correspondant = None
            for jour_planning, date_planning_str in dates_par_jour.items():
                if date_planning_str == date_demain_str:
                    jour_correspondant = jour_planning
                    print(f"✅ Date trouvée dans planning: {date_demain_str} -> {jour_correspondant}")
                    break
            
            if not jour_correspondant:
                # Essayer de parser les dates pour comparer
                print("⚠️ Date exacte non trouvée, tentative de parsing...")
                for jour_planning, date_planning_str in dates_par_jour.items():
                    try:
                        # Essayer de parser la date du planning
                        date_planning = datetime.strptime(date_planning_str, "%d/%m/%Y").date()
                        if date_planning == demain:
                            jour_correspondant = jour_planning
                            print(f"✅ Date correspondante trouvée: {date_planning} -> {jour_correspondant}")
                            break
                    except:
                        continue
            
            if not jour_correspondant:
                print(f"❌ Le planning chargé ne contient pas la date du {date_demain_str}")
                print(f"📅 Dates disponibles dans le planning: {dates_par_jour}")
                
                # Afficher les dates disponibles
                dates_disponibles = "date in dates_par_jour.items"
                
                return JsonResponse({
                    'success': False,
                    'error': "Le planning chargé ne contient pas la date actuel"
                    
                })
            
            # Utiliser le jour correspondant trouvé
            jour_a_utiliser = jour_correspondant
            print(f"📊 Recherche des agents pour: {jour_a_utiliser} ({date_demain_str})")
            
            # 5. Récupérer les agents PROGRAMMÉS pour ce jour et cette heure
            # Utiliser la même logique que dans liste_transports
            class FiltreFormPlanning:
                def __init__(self, jour, type_transport, heure_valeur):
                    self.cleaned_data = {
                        'jour': jour,
                        'type_transport': type_transport,
                        'heure_ete': False,
                        'filtre_agents': 'tous'
                    }
                    # Ajouter l'heure pour traiter_donnees
                    self.data = {'heure_specifique': str(heure_valeur)}
            
            form_filtre = FiltreFormPlanning(jour_a_utiliser, type_transport, heure_valeur)
            liste_transports = gestionnaire.traiter_donnees(form_filtre)
            
            print(f"📊 {len(liste_transports)} agent(s) programmé(s) pour {jour_a_utiliser} ({date_demain_str}) {type_transport} {heure_valeur}h")            
            # 6. Préparer la liste de TOUS les agents (disponibles ET réservés)
            agents_list = []
            total_disponibles = 0
            total_reserves = 0
            
            for transport in liste_transports:
                agent_nom = transport['agent']
                
                # Chercher l'agent dans la base de données
                agent_obj = Agent.objects.filter(nom__icontains=agent_nom).first()
                
                if agent_obj:
                    # Vérifier si l'agent est réservé
                    est_reserve = agent_obj.id in reservations_dict
                    est_mien = est_reserve and reservations_dict[agent_obj.id]['est_mienne']
                    
                    if est_reserve:
                        total_reserves += 1
                        chauffeur_reservant = reservations_dict[agent_obj.id]['chauffeur_nom']
                    else:
                        total_disponibles += 1
                        chauffeur_reservant = None
                    
                    # Ajouter l'agent à la liste (disponible OU réservé)
                    agents_list.append({
                        'id': agent_obj.id,
                        'nom': agent_obj.nom,
                        'adresse': agent_obj.adresse or 'Non spécifiée',
                        'telephone': agent_obj.telephone or 'Non spécifié',
                        'societe': agent_obj.get_societe_display(),
                        'est_complet': agent_obj.est_complet() if hasattr(agent_obj, 'est_complet') else True,
                        'planning_heure': transport.get('heure', heure_valeur),
                        'est_programme': True,
                        'est_reserve': est_reserve,
                        'est_mien': est_mien,
                        'chauffeur_reservant': chauffeur_reservant,
                        'peut_reserver': not est_reserve,  # Peut réserver seulement si pas déjà réservé
                        'reservation_id': reservations_dict[agent_obj.id]['reservation_id'] if est_reserve else None
                    })
            
            print(f"✅ {len(agents_list)} agent(s) au total: {total_disponibles} disponible(s), {total_reserves} réservé(s)")
            
            # 7. Formatage de la réponse
            return JsonResponse({
                'success': True,
                'date': demain.strftime('%Y-%m-%d'),
                'date_display': demain.strftime('%d/%m/%Y'),
                'jour_semaine': jour_semaine,
                'type_transport': type_transport,
                'heure': {
                    'id': heure_transport.id,
                    'libelle': heure_transport.libelle,
                    'valeur': heure_transport.heure,
                },
                'agents': agents_list,  # Tous les agents
                'stats': {
                    'total_agents': len(agents_list),
                    'total_disponibles': total_disponibles,
                    'total_reserves': total_reserves,
                    'disponibles_pourcent': round((total_disponibles / len(agents_list) * 100) if len(agents_list) > 0 else 0, 1)
                },
                'message': f"{total_disponibles} agent(s) disponible(s) sur {len(agents_list)}"
            })
            
        except Exception as e:
            print(f"❌ Erreur chargement planning: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Erreur chargement planning: {str(e)}'
            })
        
    except HeureTransport.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Heure non trouvée'})
    except Exception as e:
        print(f"❌ Erreur api_agents_disponibles_demain: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
# API pour l'historique
@csrf_exempt
@require_GET
def api_historique(request):
    """API pour voir toutes les courses (passées) avec filtrage par mois par défaut et les agents transportés"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        Agent = apps.get_model('gestion', 'Agent')
        
        # Récupérer l'utilisateur courant
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        is_super_chauffeur = getattr(chauffeur, 'super_chauffeur', False)
        
        # Récupérer les filtres
        date_debut_str = request.GET.get('date_debut')
        date_fin_str = request.GET.get('date_fin')
        statut_filter = request.GET.get('statut')
        
        # Base queryset - toutes les courses du chauffeur
        courses = Course.objects.filter(chauffeur_id=chauffeur_id)
        
        # Si aucune date n'est spécifiée, prendre le mois en cours par défaut
        if not date_debut_str and not date_fin_str:
            now = timezone.now()
            date_debut = datetime(now.year, now.month, 1).date()            # Dernier jour du mois
            if now.month == 12:
                date_fin = datetime(now.year + 1, 1, 1).date() - timedelta(days=1)
            else:
                date_fin = datetime(now.year, now.month + 1, 1).date() - timedelta(days=1)
            
            courses = courses.filter(date_reelle__range=[date_debut, date_fin])
            print(f"📅 Filtre par défaut: mois en cours ({date_debut} à {date_fin})")
        
        # Si seulement date début est spécifiée
        elif date_debut_str and not date_fin_str:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            courses = courses.filter(date_reelle__gte=date_debut)
            print(f"📅 Filtre: à partir de {date_debut}")
        
        # Si seulement date fin est spécifiée
        elif not date_debut_str and date_fin_str:
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
            courses = courses.filter(date_reelle__lte=date_fin)
            print(f"📅 Filtre: jusqu'à {date_fin}")
        
        # Si les deux dates sont spécifiées
        elif date_debut_str and date_fin_str:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
            courses = courses.filter(date_reelle__range=[date_debut, date_fin])
            print(f"📅 Filtre: intervalle {date_debut} à {date_fin}")
        
        # Filtrer par statut si spécifié
        if statut_filter and statut_filter != 'tous':
            courses = courses.filter(statut=statut_filter)
            print(f"📊 Filtre statut: {statut_filter}")
        
        # Trier par date (plus récent d'abord)
        courses = courses.order_by('-date_reelle', '-heure')
        
        print(f"📋 Nombre de courses trouvées: {courses.count()}")
        
        courses_data = []
        for course in courses:
            # Récupérer les agents affectés à cette course
            affectations = Affectation.objects.filter(course=course).select_related('agent')
            
            # Liste des agents avec leurs informations
            agents_list = []
            for affectation in affectations:
                if affectation.agent:
                    agents_list.append({
                        'id': affectation.agent.id,
                        'nom': affectation.agent.nom or 'Non spécifié',
                        'adresse': affectation.agent.adresse or 'Non spécifiée',
                        'telephone': affectation.agent.telephone or 'Non spécifié',
                        'societe': affectation.agent.get_societe_display() if hasattr(affectation.agent, 'get_societe_display') else 'Non spécifiée',
                    })
            
            # Prix de la course
            prix_course = course.get_prix_course() if hasattr(course, 'get_prix_course') else 0
            prix_total = float(course.prix_total or prix_course)
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%Y-%m-%d'),
                'date_display': course.date_reelle.strftime('%d/%m/%Y'),
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': affectations.count(),
                'agents': agents_list,  # Ajout de la liste des agents
                'statut': course.statut,
                'statut_display': course.get_statut_display(),
                'prix': prix_total,
                'prix_display': f"{prix_total:.2f} DNT",
                'notes': course.notes_validation or '',
                'mois': course.date_reelle.strftime('%Y-%m'),  # Pour le regroupement
            })
        
        # Statistiques
        total_courses = len(courses_data)
        courses_validees = len([c for c in courses_data if c['statut'] in ['validee', 'payee']])
        revenu_total = sum([c['prix'] for c in courses_data if c['statut'] in ['validee', 'payee']])
        
        # Calculer les dates par défaut pour l'affichage
        now = timezone.now()
        date_debut_default = datetime(now.year, now.month, 1).date()
        if now.month == 12:
            date_fin_default = datetime(now.year + 1, 1, 1).date() - timedelta(days=1)
        else:
            date_fin_default = datetime(now.year, now.month + 1, 1).date() - timedelta(days=1)
        
        return JsonResponse({
            'success': True,
            'courses': courses_data,
            'filtres': {
                'date_debut': date_debut_str or date_debut_default.strftime('%Y-%m-%d'),
                'date_fin': date_fin_str or date_fin_default.strftime('%Y-%m-%d'),
                'statut': statut_filter or 'tous',
            },
            'stats': {
                'total': total_courses,
                'validees': courses_validees,
                  'revenu_total': round(revenu_total, 2) if is_super_chauffeur else None,  # None si pas super-chauffeur
                'revenu_display': f"{round(revenu_total, 2):.2f} DNT" if is_super_chauffeur else "Non disponible",
                'periode': f"{date_debut_default.strftime('%d/%m/%Y')} - {date_fin_default.strftime('%d/%m/%Y')}"
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur historique: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
# API pour les courses de sélection
@csrf_exempt
@require_GET
def api_courses_selection(request):
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        date_str = request.GET.get('date', None)
        if date_str:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            selected_date = timezone.now().date()
        
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        courses = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            date_reelle=selected_date
        ).order_by('heure')
        
        courses_data = []
        for course in courses:
            agents_data = []
            
            try:
                affectations = course.affectation_set.select_related('agent').all()
                
                for affectation in affectations[:3]:
                    if affectation.agent:
                        agents_data.append({
                            'nom': affectation.agent.nom or 'Non spécifié',
                            'adresse': affectation.agent.adresse or 'Non spécifié',
                        })
                
                if affectations.count() > 3:
                    agents_data.append({
                        'nom': f'+ {affectations.count() - 3} autres',
                        'adresse': ''
                    })
                    
            except Exception as e:
                print(f"⚠️ Erreur agents pour course {course.id}: {e}")
                agents_data = []
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%d/%m/%Y'),
                'type_transport': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': course.affectation_set.count(),
                'agents': agents_data,
                'statut': course.statut,
                'statut_display': course.get_statut_display() if hasattr(course, 'get_statut_display') else course.statut,
                'prix': float(course.get_prix_course() or 0) if hasattr(course, 'get_prix_course') else 0,
                'peut_valider': course.statut in ['en_attente', 'en_cours'],
            })
        
        return JsonResponse({
            'success': True,
            'courses': courses_data,
            'date': selected_date.strftime('%Y-%m-%d'),
            'date_display': selected_date.strftime('%d/%m/%Y'),
            'total': len(courses_data),
            'message': f"{len(courses_data)} courses trouvées"
        })
        
    except Exception as e:
        print(f"❌ Erreur courses_selection: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'courses': [],
            'total': 0
        })

# API pour annuler une course
@csrf_exempt
@require_POST
def api_annuler_course(request):
    """API pour annuler une course"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        
        Course = apps.get_model('gestion', 'Course')
        course = Course.objects.get(id=course_id, chauffeur_id=chauffeur_id)
        
        course.statut = 'annulee'
        course.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Course annulée',
            'statut': course.statut,
            'statut_display': 'Annulée'
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Course non trouvée'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# API pour créer une course

@csrf_exempt
@require_POST
def api_creer_course(request):
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        date_str = data.get('date')
        type_transport = data.get('type_transport')
        heure = data.get('heure')
        agents_ids = data.get('agents', [])
        
        print("="*60)
        print(f"📝 CRÉATION COURSE")
        print(f"📅 Date reçue: {date_str}")
        print(f"🚗 Type: {type_transport}")
        print(f"⏰ Heure: {heure}")
        print(f"👥 Agents IDs reçus: {agents_ids}")
        print("="*60)
        
        # Vérification des données
        if not date_str:
            return JsonResponse({'success': False, 'error': 'Date manquante'}, status=400)
        
        if not type_transport:
            return JsonResponse({'success': False, 'error': 'Type de transport manquant'}, status=400)
        
        if heure is None:
            return JsonResponse({'success': False, 'error': 'Heure manquante'}, status=400)
        
        if not agents_ids or len(agents_ids) == 0:
            return JsonResponse({'success': False, 'error': 'Aucun agent sélectionné'}, status=400)
        
        from datetime import datetime
        from django.utils import timezone
        
        # 🇫🇷 SOLUTION CRITIQUE : Utiliser l'heure du SERVEUR (pas l'heure du téléphone)
        # timezone.now() utilise le fuseau horaire configuré dans Django (settings.TIME_ZONE)
        # Normalement configuré à 'Europe/Paris' pour l'heure française
        maintenant = timezone.now()
        
        heure_actuelle = maintenant.hour
        date_actuelle = maintenant.date()
        
        print(f"🇫🇷 HEURE DU SERVEUR (France): {heure_actuelle}h")
        print(f"🇫🇷 DATE DU SERVEUR: {date_actuelle}")
        print(f"🕐 Heure complète du serveur: {maintenant.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Format de date invalide'}, status=400)
        
        heure_int = int(heure)
        
        print(f"⏰ Vérification: Heure demandée: {heure_int}h, Heure serveur: {heure_actuelle}h")
        print(f"📅 Date demandée: {date_obj}, Date serveur: {date_actuelle}")
        
        # ✅ Gestion du cycle de travail 6h-4h avec l'heure du serveur
        date_a_utiliser = date_obj
        
        if heure_actuelle >= 6:
            # On est dans la journée de travail (6h à 23h59)
            if date_obj != date_actuelle:
                return JsonResponse({
                    'success': False,
                    'error': "Vous ne pouvez créer des courses que pour aujourd'hui (heure du serveur)"
                }, status=400)
        else:
            # On est dans la nuit (00h à 5h) - ça fait partie de la journée d'hier
            date_hier = date_actuelle - timedelta(days=1)
            
            if date_obj == date_actuelle:
                print(f"🌙 Nuit détectée (actuellement {heure_actuelle}h) - Redirection vers hier ({date_hier})")
                date_a_utiliser = date_hier
            elif date_obj == date_hier:
                print(f"✅ Date demandée correspond à hier ({date_hier}) - OK")
                date_a_utiliser = date_hier
            else:
                return JsonResponse({
                    'success': False,
                    'error': f"Entre 00h et 5h (heure serveur), vous ne pouvez créer des courses que pour {date_hier}"
                }, status=400)
        
        print(f"📅 Date utilisée pour la création: {date_a_utiliser}")
        
        # Vérification des heures selon l'heure du serveur
        if heure_actuelle >= 6:
            if heure_int > heure_actuelle:
                print(f"  ❌ Heure future {heure_int}h > {heure_actuelle}h - INTERDITE")
                return JsonResponse({
                    'success': False,
                    'error': f"Vous ne pouvez pas créer une course pour {heure_int}h (heure future selon le serveur). Les courses ne peuvent être créées que pour les heures déjà passées."
                }, status=400)
            else:
                print(f"  ✅ Heure {heure_int}h (passée ou actuelle) - autorisée")
        else:
            print(f"  ✅ Nuit détectée - toutes les heures sont considérées comme passées")
        
        # Conversion du jour en français
        jours_fr = {
            'Monday': 'Lundi',
            'Tuesday': 'Mardi',
            'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi',
            'Friday': 'Vendredi',
            'Saturday': 'Samedi',
            'Sunday': 'Dimanche'
        }
        
        jour_anglais = date_a_utiliser.strftime('%A')
        jour_francais = jours_fr.get(jour_anglais, jour_anglais)
        
        print(f"📅 Jour: {jour_anglais} -> {jour_francais}")
        
        # =================================================
        
        from django.apps import apps
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Agent = apps.get_model('gestion', 'Agent')
        
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        # ========== VÉRIFIER SI LA COURSE EXISTE DÉJÀ ==========
        course_existante = Course.objects.filter(
            chauffeur=chauffeur,
            date_reelle=date_a_utiliser,
            type_transport=type_transport,
            heure=heure_int
        ).first()
        
        if course_existante:
            print(f"⚠️ Course déjà existante ID: {course_existante.id}")
            agents_deja_affectes = Affectation.objects.filter(
                course=course_existante,
                agent_id__in=agents_ids
            ).values_list('agent_id', flat=True)
            
            agents_a_ajouter = [aid for aid in agents_ids if aid not in agents_deja_affectes]
            
            if not agents_a_ajouter:
                return JsonResponse({
                    'success': True,
                    'message': 'Course déjà existante',
                    'course_id': course_existante.id,
                    'agents_affectes': [a.nom for a in course_existante.affectation_set.select_related('agent').all() if a.agent]
                })
            
            course = course_existante
            created = False
        else:
            course = Course(
                chauffeur=chauffeur,
                date_reelle=date_a_utiliser,
                type_transport=type_transport,
                heure=heure_int,
                jour=jour_francais,
                statut='en_attente'
            )
            course.save()
            created = True
            print(f"✅ Nouvelle course créée ID: {course.id} avec jour: {jour_francais}")
        
        # ========== CHARGER LE PLANNING ==========
        agents_hors_planning = []
        planning_charge = False
        agents_programmes = []
        
        try:
            from gestion.utils import GestionnaireTransport
            
            gestionnaire = GestionnaireTransport()
            
            if gestionnaire.recharger_planning_depuis_session():
                planning_charge = True
                print("✅ Planning chargé depuis la session")
                
                date_str_formatted = date_a_utiliser.strftime("%d/%m/%Y")
                
                jour_correspondant = None
                for jour_planning, date_planning_str in gestionnaire.dates_par_jour.items():
                    if date_planning_str == date_str_formatted:
                        jour_correspondant = jour_planning
                        print(f"✅ Date trouvée: {date_str_formatted} -> {jour_correspondant}")
                        break
                
                if jour_correspondant:
                    class FiltreFormPlanning:
                        def __init__(self, jour, type_transport, heure_valeur):
                            self.cleaned_data = {
                                'jour': jour,
                                'type_transport': type_transport,
                                'heure_ete': False,
                                'filtre_agents': 'tous'
                            }
                            self.data = {'heure_specifique': str(heure_int)}
                    
                    form_filtre = FiltreFormPlanning(jour_correspondant, type_transport, heure_int)
                    liste_transports = gestionnaire.traiter_donnees(form_filtre)
                    
                    agents_programmes = [t['agent'].strip().lower() for t in liste_transports]
                    print(f"📋 Agents programmés ({len(agents_programmes)}): {agents_programmes[:10]}")
        except Exception as e:
            print(f"⚠️ Erreur chargement planning: {e}")
        
        # ========== AJOUTER LES AFFECTATIONS ==========
        agents_affectes = []
        agents_non_trouves = []
        notifications_crees = 0
        super_notifications_crees = 0
        
        for agent_id in agents_ids:
            try:
                if isinstance(agent_id, str):
                    try:
                        agent_id = int(agent_id)
                    except ValueError:
                        agents_non_trouves.append(agent_id)
                        continue
                
                agent = Agent.objects.get(id=agent_id)
                print(f"✅ Agent trouvé: {agent.nom} (ID: {agent.id})")
                
                existe_deja = Affectation.objects.filter(
                    agent=agent,
                    date_reelle=date_a_utiliser,
                    heure=heure_int
                ).exists()
                
                if not existe_deja:
                    affectation = Affectation.objects.create(
                        course=course,
                        chauffeur=chauffeur,
                        agent=agent,
                        type_transport=type_transport,
                        heure=heure_int,
                        jour=jour_francais,
                        date_reelle=date_a_utiliser,
                        prix_course=course.get_prix_course() if hasattr(course, 'get_prix_course') else 0
                    )
                    agents_affectes.append(agent)
                    print(f"  ✅ Agent {agent.nom} affecté")
                    
                    if planning_charge and agents_programmes:
                        nom_normalise = agent.nom.strip().lower()
                        
                        if nom_normalise not in agents_programmes:
                            print(f"  🚨 AGENT HORS PLANNING: {agent.nom}")
                            agents_hors_planning.append(agent)
                            
                            try:
                                from gestion.models import NotificationAdmin
                                
                                NotificationAdmin.objects.create(
                                    titre=f"🚨 Agent hors planning - {agent.nom}",
                                    message=(
                                        f"L'agent **{agent.nom}** a été transporté par "
                                        f"**{chauffeur.nom}** le **{course.date_reelle}** "
                                        f"à **{course.heure}h** alors qu'il n'était pas programmé."
                                    ),
                                    lien=f"/admin/gestion/course/{course.id}/",
                                    type='danger',
                                    lu=False
                                )
                                notifications_crees += 1
                            except Exception as e:
                                print(f"  ❌ Erreur création notification admin: {e}")
                            
                            try:
                                from chauffeurs_mobile.models import MobileNotification
                                
                                super_chauffeurs = Chauffeur.objects.filter(
                                    super_chauffeur=True,
                                    actif=True
                                )
                                
                                for super_chauffeur in super_chauffeurs:
                                    if super_chauffeur.id == chauffeur.id:
                                        continue
                                    
                                    MobileNotification.objects.create(
                                        chauffeur=super_chauffeur,
                                        type_notification='alerte',
                                        message=f"🚨 Agent {agent.nom} transporté hors planning par {chauffeur.nom} à {course.heure}h",
                                        data={
                                            'agent_nom': agent.nom,
                                            'agent_id': agent.id,
                                            'chauffeur_nom': chauffeur.nom,
                                            'chauffeur_id': chauffeur.id,
                                            'course_id': course.id,
                                            'date': course.date_reelle.strftime('%d/%m/%Y'),
                                            'heure': course.heure,
                                            'type_transport': type_transport,
                                            'type': 'hors_planning'
                                        },
                                        vue=False
                                    )
                                    super_notifications_crees += 1
                            except Exception as e:
                                print(f"  ❌ Erreur création notification super: {e}")
                else:
                    print(f"⚠️ Agent {agent.nom} déjà affecté à {heure_int}h")
                    
            except Agent.DoesNotExist:
                print(f"❌ Agent ID {agent_id} non trouvé")
                agents_non_trouves.append(agent_id)
                continue
            except Exception as e:
                print(f"❌ Erreur pour agent {agent_id}: {e}")
                agents_non_trouves.append(agent_id)
                continue
        
        if course.statut == 'en_attente':
            course.save()
        
        total_notifications = notifications_crees + super_notifications_crees
        
        response_data = {
            'success': True,
            'message': f'Course créée avec {len(agents_affectes)} agent(s)',
            'course_id': course.id,
            'agents_affectes': [a.nom for a in agents_affectes],
            'created': created,
            'date_utilisee': date_a_utiliser.isoformat(),
            'jour_francais': jour_francais,
            'date_originale': date_str,
            'nuit_mode': heure_actuelle < 6,
            'debug': {
                'planning_charge': planning_charge,
                'agents_programmes_count': len(agents_programmes),
                'hors_planning_count': len(agents_hors_planning),
                'notifications_admin': notifications_crees,
                'notifications_super': super_notifications_crees,
                'agents_non_trouves': agents_non_trouves,
                'heure_serveur': heure_actuelle,
                'date_serveur': date_actuelle.isoformat()
            }
        }
        
        if agents_hors_planning:
            response_data['hors_planning'] = {
                'count': len(agents_hors_planning),
                'agents': [a.nom for a in agents_hors_planning]
            }
        
        print("="*60)
        print(f"✅ Course créée avec {len(agents_affectes)} agents")
        print(f"📅 Jour enregistré: {jour_francais}")
        print("="*60)
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"❌ Erreur création course: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_GET
def api_agents_disponibles(request):
    """API pour voir les agents disponibles - CORRIGÉ POUR CYCLE 6h-4h"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        # Récupérer les paramètres
        date_str = request.GET.get('date')
        type_transport = request.GET.get('type_transport')
        heure = request.GET.get('heure')
        
        if not date_str:
            date_str = timezone.now().date().isoformat()
        
        if not all([date_str, type_transport, heure]):
            return JsonResponse({'success': False, 'error': 'Paramètres manquants'})
        
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        maintenant = timezone.now()
        maintenant_heure = maintenant.hour
        maintenant_date = maintenant.date()
        heure_int = int(heure)
        
        print(f"🔍 Recherche agents pour: {date_obj} - {type_transport} - {heure_int}h")
        print(f"🕐 Heure actuelle: {maintenant_heure}h, Date actuelle: {maintenant_date}")
        
        # ✅ CORRECTION: Gestion du cycle de travail 6h-4h
        # Une journée de travail commence à 6h et se termine à 4h le lendemain
        date_a_utiliser = date_obj
        
        # Déterminer si la date demandée correspond à la journée de travail actuelle
        if maintenant_heure >= 6:
            # On est dans la journée de travail (6h à 23h59)
            if date_obj != maintenant_date:
                return JsonResponse({
                    'success': False,
                    'error': "Vous ne pouvez créer des courses que pour aujourd'hui"
                })
        else:
            # On est dans la nuit (00h à 5h) - ça fait partie de la journée d'hier
            date_hier = maintenant_date - timedelta(days=1)
            
            if date_obj == maintenant_date:
                # Si l'utilisateur demande aujourd'hui, on lui propose hier (car c'est la même nuit)
                print(f"🌙 Nuit détectée (actuellement {maintenant_heure}h) - Redirection vers hier ({date_hier})")
                date_a_utiliser = date_hier
            elif date_obj == date_hier:
                print(f"✅ Date demandée correspond à hier ({date_hier}) - OK")
                date_a_utiliser = date_hier
            else:
                return JsonResponse({
                    'success': False,
                    'error': f"Entre 00h et 5h, vous ne pouvez créer des courses que pour {date_hier}"
                })
        
        print(f"📅 Date utilisée pour la recherche: {date_a_utiliser}")
        
        # ========== CHARGER LE PLANNING ==========
        agents_programmes = None
        planning_info = {"charge": False, "message": ""}
        
        try:
            from gestion.utils import GestionnaireTransport
            
            gestionnaire = GestionnaireTransport()
            
            if gestionnaire.recharger_planning_depuis_session():
                jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
                date_str_formatted = date_a_utiliser.strftime("%d/%m/%Y")
                
                jour_correspondant = None
                for jour_planning, date_planning_str in gestionnaire.dates_par_jour.items():
                    if date_planning_str == date_str_formatted:
                        jour_correspondant = jour_planning
                        break
                
                if jour_correspondant:
                    class FiltreFormPlanning:
                        def __init__(self, jour, type_transport, heure_valeur):
                            self.cleaned_data = {
                                'jour': jour,
                                'type_transport': type_transport,
                                'heure_ete': False,
                                'filtre_agents': 'tous'
                            }
                            self.data = {'heure_specifique': str(heure_int)}
                    
                    form_filtre = FiltreFormPlanning(jour_correspondant, type_transport, heure_int)
                    liste_transports = gestionnaire.traiter_donnees(form_filtre)
                    agents_programmes = [t['agent'].strip().lower() for t in liste_transports]
                    planning_info = {"charge": True, "message": f"{len(agents_programmes)} agent(s) programmé(s)"}
                    
        except Exception as e:
            print(f"⚠️ Erreur planning: {e}")
        
        # ========== VÉRIFIER COURSE EXISTANTE ==========
        course_existante = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            date_reelle=date_a_utiliser,
            type_transport=type_transport,
            heure=heure_int
        ).first()
        
        if course_existante:
            agents_affectes = course_existante.affectation_set.all()
            return JsonResponse({
                'success': True,
                'course_id': course_existante.id,
                'agents_affectes': [{'id': a.agent.id, 'nom': a.agent.nom} for a in agents_affectes],
                'statut_course': course_existante.statut
            })
        
        # ========== RÉCUPÉRER LES AGENTS ==========
        affectations_aujourdhui = Affectation.objects.filter(date_reelle=date_a_utiliser)
        
        agents_occupes_par_heure = {}
        for affectation in affectations_aujourdhui:
            try:
                course = affectation.course
                if course and course.heure is not None:
                    heure_course = course.heure
                    if heure_course not in agents_occupes_par_heure:
                        agents_occupes_par_heure[heure_course] = []
                    agents_occupes_par_heure[heure_course].append(affectation.agent_id)
            except:
                pass
        
        agents_exclus_par_heure = agents_occupes_par_heure.get(heure_int, [])
        print(f"🕒 {heure_int}h: {len(agents_exclus_par_heure)} agent(s) exclus")
        
        reservations_date = Reservation.objects.filter(
            date_reservation=date_a_utiliser,
            statut__in=['reservee', 'confirmee']
        ).select_related('chauffeur', 'agent')
        
        reservations_filtrees = [r for r in reservations_date if r.type_transport == type_transport]
        
        tous_agents = Agent.objects.filter(voiture_personnelle=False).order_by('nom')
        
        reservations_par_agent = {}
        for reservation in reservations_filtrees:
            reservations_par_agent[reservation.agent_id] = {
                'chauffeur_nom': reservation.chauffeur.nom,
                'est_mien': reservation.chauffeur_id == int(chauffeur_id),
                'reservation_id': reservation.id,
            }
        
        agents_reserves = []
        agents_disponibles = []
        agents_exclus = []
        
        for agent in tous_agents:
            est_programme = True
            if agents_programmes is not None:
                est_programme = agent.nom.strip().lower() in agents_programmes
            
            agent_data = {
                'id': agent.id,
                'nom': agent.nom,
                'adresse': agent.adresse or 'Non spécifiée',
                'telephone': agent.telephone or 'Non spécifié',
                'societe': agent.get_societe_display(),
                'est_complet': agent.est_complet() if hasattr(agent, 'est_complet') else True,
                'est_programme': est_programme,
                'peut_reserver': True
            }
            
            if agent.id in agents_exclus_par_heure:
                agent_data['est_exclu'] = True
                agent_data['peut_reserver'] = False
                agent_data['message'] = f"Déjà dans une course à {heure_int}h"
                agents_exclus.append(agent_data)
                continue
            
            if agent.id in reservations_par_agent:
                agent_data.update(reservations_par_agent[agent.id])
                agent_data['est_reserve'] = True
                agent_data['peut_reserver'] = True
                agents_reserves.append(agent_data)
            else:
                agents_disponibles.append(agent_data)
        
        agents_disponibles_programmes = [a for a in agents_disponibles if a.get('est_programme', True)]
        agents_disponibles_non_programmes = [a for a in agents_disponibles if not a.get('est_programme', True)]
        
        agents_final = []
        agents_final.extend(agents_disponibles_programmes)
        agents_final.extend(agents_disponibles_non_programmes)
        agents_final.extend(agents_reserves)
        
        stats = {
            'total': len(agents_final),
            'disponibles': len(agents_disponibles),
            'reserves': len(agents_reserves),
            'programmes': len(agents_disponibles_programmes),
            'non_programmes': len(agents_disponibles_non_programmes),
            'exclus': len(agents_exclus),
            'mes_reserves': len([a for a in agents_reserves if a.get('est_mien', False)])
        }
        
        return JsonResponse({
            'success': True,
            'agents': agents_final,
            'stats': stats,
            'planning_info': planning_info,
            'date': date_a_utiliser.isoformat(),
            'date_originale': date_str,
            'type_transport': type_transport,
            'heure': heure_int,
            'nuit_mode': maintenant_heure < 6
        })
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def api_terminer_course(request):
    """API pour qu'un chauffeur termine une course"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        
        Course = apps.get_model('gestion', 'Course')
        course = Course.objects.get(id=course_id, chauffeur_id=chauffeur_id)
        
        if course.statut not in ['en_attente', 'en_cours']:
            return JsonResponse({
                'success': False, 
                'error': f'Course déjà {course.get_statut_display()}'
            })
        
        course.statut = 'terminee'
        course.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Course terminée avec succès',
            'statut': course.statut,
            'statut_display': course.get_statut_display()
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Course non trouvée'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# API pour demander validation
@csrf_exempt
@require_POST
def api_demander_validation(request):
    """API pour qu'un chauffeur demande la validation d'une course"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        notes = data.get('notes', '')
        
        Course = apps.get_model('gestion', 'Course')
        course = Course.objects.get(id=course_id, chauffeur_id=chauffeur_id)
        
        if course.statut != 'terminee':
            return JsonResponse({
                'success': False, 
                'error': 'La course doit être terminée avant validation'
            })
        
        # Utiliser la méthode du modèle si elle existe
        if hasattr(course, 'demander_validation'):
            course.demander_validation(notes)
        else:
            # Fallback
            course.statut = 'demande_validation'
            course.notes_validation = notes
            course.demande_validation_at = timezone.now()
            course.save()
        
        return JsonResponse({
            'success': True,
            'message': "Demande de validation envoyée à l'admin",
            'statut': course.statut,
            'statut_display': course.get_statut_display()
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Course non trouvée'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# API pour voir les courses VALIDÉES
@csrf_exempt
@require_GET
def api_courses_validees(request):
    """API pour voir les courses VALIDÉES par l'admin"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Courses VALIDÉES seulement (statut='validee')
        courses = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            statut='validee'
        ).order_by('-date_reelle', '-heure')
        
        courses_data = []
        total_montant = 0
        
        for course in courses:
            # Compter les agents
            nb_agents = Affectation.objects.filter(course=course).count()
            
            # Calculer le montant
            montant = 0
            if hasattr(course, 'prix_total') and course.prix_total:
                montant = float(course.prix_total)
            elif hasattr(course, 'get_prix_course'):
                montant = float(course.get_prix_course() or 0)
            
            total_montant += montant
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%Y-%m-%d'),
                'date_display': course.date_reelle.strftime('%d/%m/%Y'),
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': nb_agents,
                'montant': montant,
                'montant_display': f"{montant:.2f} DNT",
                'statut': course.statut,
                'statut_display': 'Validée',
            })
        
        return JsonResponse({
            'success': True,
            'courses': courses_data,
            'stats': {
                'total': len(courses_data),
                'total_montant': total_montant,
                'total_montant_display': f"{total_montant:.2f} DNT",
            },
            'message': f"{len(courses_data)} courses validées"
        })
        
    except Exception as e:
        print(f"❌ Erreur courses_validees: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'courses': [],
            'stats': {'total': 0, 'total_montant': 0}
        })

# API pour voir les courses EN ATTENTE
@csrf_exempt
@require_GET
def api_courses_en_attente(request):
    """API pour voir les courses EN ATTENTE de validation admin"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Courses EN ATTENTE seulement (statut='en_attente')
        courses = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            statut='en_attente'
        ).order_by('-created_at', 'date_reelle', 'heure')
        
        courses_data = []
        
        for course in courses:
            nb_agents = Affectation.objects.filter(course=course).count()
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%Y-%m-%d'),
                'date_display': course.date_reelle.strftime('%d/%m/%Y'),
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': nb_agents,
                'statut': course.statut,
                'statut_display': 'En attente',
                'created_at': course.created_at.strftime('%d/%m/%Y %H:%M') if hasattr(course, 'created_at') else '',
            })
        
        return JsonResponse({
            'success': True,
            'courses': courses_data,
            'total': len(courses_data),
            'message': f"{len(courses_data)} courses en attente de validation"
        })
        
    except Exception as e:
        print(f"❌ Erreur courses_en_attente: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'courses': [],
            'total': 0
        })

# API pour voir les courses ANNULÉES
@csrf_exempt
@require_GET
def api_courses_annulees(request):
    """API pour voir les courses ANNULÉES par l'admin"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Courses ANNULÉES seulement (statut='annulee')
        courses = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            statut='annulee'
        ).order_by('-date_reelle', '-heure')
        
        courses_data = []
        
        for course in courses:
            nb_agents = Affectation.objects.filter(course=course).count()
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%Y-%m-%d'),
                'date_display': course.date_reelle.strftime('%d/%m/%Y'),
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': nb_agents,
                'statut': course.statut,
                'statut_display': 'Annulée',
                'notes_validation': course.notes_validation or 'Non spécifiée',
            })
        
        return JsonResponse({
            'success': True,
            'courses': courses_data,
            'total': len(courses_data),
            'message': f"{len(courses_data)} courses annulées"
        })
        
    except Exception as e:
        print(f"❌ Erreur courses_annulees: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'courses': [],
            'total': 0
        })
@csrf_exempt
@require_GET
def api_super_chauffeurs_list(request):
    """API pour voir tous les chauffeurs (super-chauffeur seulement)"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    print(f"🔍 API super/chauffeurs/ appelée - Session: {dict(request.session)}")
    print(f"🔍 Chauffeur ID depuis session: {chauffeur_id}")
    
    if not chauffeur_id:
        print("❌ Pas de chauffeur_id dans la session")
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        # Importer les modèles de manière robuste
        try:
            from django.apps import apps
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
            Course = apps.get_model('gestion', 'Course')
        except Exception as e:
            print(f"❌ Erreur import modèles: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Modèles non disponibles: {str(e)}'
            })
        
        # Vérifier si c'est un super-chauffeur
        try:
            chauffeur = Chauffeur.objects.get(id=chauffeur_id)
            print(f"✅ Chauffeur trouvé: {chauffeur.nom}")
            print(f"🔍 Champs du modèle: {[f.name for f in chauffeur._meta.fields]}")
            
            # Vérifier le champ super_chauffeur
            if hasattr(chauffeur, 'super_chauffeur'):
                is_super = chauffeur.super_chauffeur
                print(f"🎯 super_chauffeur attribut direct: {is_super}")
            else:
                # Vérifier si le champ existe dans la base de données
                print("⚠️ Champ 'super_chauffeur' non trouvé dans le modèle")
                
                # Fallback : autoriser l'accès pour le test
                is_super = True  # Pour le test, autoriser l'accès
                print("⚠️ ATTENTION: Champ super_chauffeur non défini - autorisation temporaire")
            
            print(f"🎯 Est super chauffeur? {is_super}")
            
            if not is_super:
                print("❌ Le chauffeur n'est PAS un super_chauffeur")
                return JsonResponse({
                    'success': False,
                    'error': 'Accès réservé aux super-chauffeurs',
                    'is_super': False,
                    'champs_model': [f.name for f in chauffeur._meta.fields]  # Debug
                }, status=403)
                
        except Chauffeur.DoesNotExist:
            print(f"❌ Chauffeur {chauffeur_id} non trouvé")
            return JsonResponse({'success': False, 'error': 'Chauffeur non trouvé'})
        
        print("✅ Le chauffeur EST un super_chauffeur - continuer...")
        
        # Récupérer TOUS les chauffeurs (pas seulement actifs pour le test)
        all_chauffeurs = Chauffeur.objects.all().order_by('nom')
        print(f"📊 {all_chauffeurs.count()} chauffeur(s) trouvé(s)")
        
        chauffeurs_data = []
        today = timezone.now().date()
        
        for ch in all_chauffeurs:
            # Compter les courses du mois (simplifié)
            courses_count = Course.objects.filter(
                chauffeur=ch,
                date_reelle__year=today.year,
                date_reelle__month=today.month
            ).count()
            
            # Compter les courses validées
            courses_validees = Course.objects.filter(
                chauffeur=ch,
                date_reelle__year=today.year,
                date_reelle__month=today.month,
                statut__in=['validee', 'payee']
            ).count()
            
            # Calculer le revenu (simplifié)
            revenu = 0
            try:
                courses_val = Course.objects.filter(
                    chauffeur=ch,
                    date_reelle__year=today.year,
                    date_reelle__month=today.month,
                    statut__in=['validee', 'payee']
                )
                for course in courses_val:
                    if hasattr(course, 'prix_total') and course.prix_total:
                        try:
                            revenu += float(course.prix_total)
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                print(f"⚠️ Erreur calcul revenu {ch.id}: {e}")
            
            chauffeur_info = {
                'id': ch.id,
                'nom': ch.nom,
                'telephone': ch.telephone,
                'type_chauffeur': getattr(ch, 'type_chauffeur', 'taxi'),
                'vehicule': getattr(ch, 'numero_voiture', 'Non spécifié'),
                'actif': ch.actif,
                'super_chauffeur': getattr(ch, 'super_chauffeur', False),
            }
            
            # Ajouter statistiques
            chauffeur_info['statistiques'] = {
                'courses_mois': courses_count,
                'courses_validees': courses_validees,
                'revenu_mois': round(revenu, 2) if revenu else 0,
                'moyenne_course': round(revenu / courses_validees, 2) if courses_validees > 0 else 0
            }
            
            chauffeurs_data.append(chauffeur_info)
        
        return JsonResponse({
            'success': True,
            'is_super_chauffeur': True,
            'chauffeurs': chauffeurs_data,
            'total': len(chauffeurs_data),
            'periode': f"{today.strftime('%m/%Y')}",
            'debug_info': {
                'chauffeur_session_id': chauffeur_id,
                'chauffeur_nom': chauffeur.nom,
                'super_chauffeur': getattr(chauffeur, 'super_chauffeur', False)
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur api_super_chauffeurs_list: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()[:500]
        })
@csrf_exempt
@require_GET
def api_super_chauffeur_detail(request, chauffeur_id):
    """API pour voir le détail d'un chauffeur (super-chauffeur seulement)"""
    current_chauffeur_id = request.session.get('chauffeur_id')
    
    if not current_chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Vérifier si c'est un super-chauffeur
        current_chauffeur = Chauffeur.objects.get(id=current_chauffeur_id)
        
        if not getattr(current_chauffeur, 'super_chauffeur', False):
            return JsonResponse({
                'success': False,
                'error': 'Accès réservé aux super-chauffeurs'
            }, status=403)
        
        # Récupérer le chauffeur cible
        target_chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        # Récupérer les courses récentes (30 derniers jours)
        date_debut = timezone.now().date() - timedelta(days=30)
        courses = Course.objects.filter(
            chauffeur=target_chauffeur,
            date_reelle__gte=date_debut
        ).order_by('-date_reelle', '-heure')
        
        courses_data = []
        total_revenu = 0
        
        for course in courses:
            nb_agents = Affectation.objects.filter(course=course).count()
            prix = 0
            if hasattr(course, 'prix_total') and course.prix_total:
                prix = float(course.prix_total)
            elif hasattr(course, 'get_prix_course'):
                prix = float(course.get_prix_course() or 0)
            
            if course.statut in ['validee', 'payee']:
                total_revenu += prix
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%Y-%m-%d'),
                'date_display': course.date_reelle.strftime('%d/%m/%Y'),
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': nb_agents,
                'statut': course.statut,
                'statut_display': course.get_statut_display(),
                'prix': prix,
                'prix_display': f"{prix:.2f} DNT",
                'notes': course.notes_validation or ''
            })
        
        # Statistiques globales
        total_courses = Course.objects.filter(chauffeur=target_chauffeur).count()
        total_validees = Course.objects.filter(
            chauffeur=target_chauffeur,
            statut__in=['validee', 'payee']
        ).count()
        
        # Revenu total
        all_courses = Course.objects.filter(
            chauffeur=target_chauffeur,
            statut__in=['validee', 'payee']
        )
        revenu_total = 0
        for course in all_courses:
            if hasattr(course, 'prix_total') and course.prix_total:
                revenu_total += float(course.prix_total)
        
        return JsonResponse({
            'success': True,
            'is_super_chauffeur': True,
            'current_chauffeur': {
                'id': current_chauffeur.id,
                'nom': current_chauffeur.nom,
                'super_chauffeur': True
            },
            'target_chauffeur': {
                'id': target_chauffeur.id,
                'nom': target_chauffeur.nom,
                'telephone': target_chauffeur.telephone,
                'type_chauffeur': target_chauffeur.type_chauffeur,
                'vehicule': target_chauffeur.numero_voiture,
                'actif': target_chauffeur.actif,
                'super_chauffeur': getattr(target_chauffeur, 'super_chauffeur', False),
                'adresse': getattr(target_chauffeur, 'adresse', ''),
                'email': getattr(target_chauffeur, 'email', ''),
                'societe': getattr(target_chauffeur, 'societe', '')
            },
            'courses': courses_data,
            'statistiques': {
                'total_courses': total_courses,
                'total_validees': total_validees,
                'total_revenu': round(revenu_total, 2),
                'moyenne_mensuelle': round(revenu_total / 12, 2) if revenu_total > 0 else 0,
                'courses_30_jours': len(courses_data),
                'revenu_30_jours': round(total_revenu, 2)
            }
        })
        
    except Chauffeur.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Chauffeur non trouvé'})
    except Exception as e:
        print(f"❌ Erreur api_super_chauffeur_detail: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_GET
def api_super_courses_today(request):
    """API pour voir toutes les courses d'aujourd'hui (super-chauffeur seulement)"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Vérifier si c'est un super-chauffeur
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        if not getattr(chauffeur, 'super_chauffeur', False):
            return JsonResponse({
                'success': False,
                'error': 'Accès réservé aux super-chauffeurs'
            }, status=403)
        
        # Date d'aujourd'hui
        aujourd_hui = timezone.now().date()
        
        # Récupérer toutes les courses d'aujourd'hui
        courses = Course.objects.filter(date_reelle=aujourd_hui).order_by('heure', 'chauffeur__nom')
        
        courses_data = []
        
        for course in courses:
            nb_agents = Affectation.objects.filter(course=course).count()
            
            # Récupérer les agents
            agents = Affectation.objects.filter(course=course).select_related('agent')
            agents_list = []
            for affectation in agents[:3]:  # Limiter à 3 pour l'affichage
                if affectation.agent:
                    agents_list.append(affectation.agent.nom)
            
            courses_data.append({
                'id': course.id,
                'chauffeur_id': course.chauffeur.id,
                'chauffeur_nom': course.chauffeur.nom,
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': nb_agents,
                'agents': agents_list,
                'agents_count': nb_agents,
                'statut': course.statut,
                'statut_display': course.get_statut_display(),
                'prix': float(course.get_prix_course() or 0) if hasattr(course, 'get_prix_course') else 0,
            })
        
        # Statistiques
        total_courses = courses.count()
        courses_validees = courses.filter(statut__in=['validee', 'payee']).count()
        courses_en_cours = courses.filter(statut__in=['en_attente', 'en_cours']).count()
        courses_terminees = courses.filter(statut='terminee').count()
        
        return JsonResponse({
            'success': True,
            'is_super_chauffeur': True,
            'date': aujourd_hui.strftime('%d/%m/%Y'),
            'courses': courses_data,
            'statistiques': {
                'total': total_courses,
                'validees': courses_validees,
                'en_cours': courses_en_cours,
                'terminees': courses_terminees,
                'chauffeurs_actifs': len(set([c['chauffeur_id'] for c in courses_data]))
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur api_super_courses_today: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
@csrf_exempt
@require_GET
def api_super_historique_global(request):
    """API historique global - DONNÉES RÉELLES"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Récupérer les modèles
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Vérifier super-chauffeur
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        if not getattr(chauffeur, 'super_chauffeur', False):
            return JsonResponse({'success': False, 'error': 'Accès réservé aux super-chauffeurs'}, status=403)
        
        print(f"✅ Super chauffeur {chauffeur.nom} - HISTORIQUE GLOBAL RÉEL")
        
        # ========== DATES ==========
        date_debut_str = request.GET.get('date_debut')
        date_fin_str = request.GET.get('date_fin')
        
        # Mois en cours par défaut
        today = timezone.now().date()
        if not date_debut_str:
            date_debut = datetime(today.year, today.month, 1).date()
            date_debut_str = date_debut.strftime('%Y-%m-%d')
        else:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        
        if not date_fin_str:
            if today.month == 12:
                date_fin = datetime(today.year + 1, 1, 1).date() - timedelta(days=1)
            else:
                date_fin = datetime(today.year, today.month + 1, 1).date() - timedelta(days=1)
            date_fin_str = date_fin.strftime('%Y-%m-%d')
        else:
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        
        print(f"📅 Période: {date_debut} → {date_fin}")
        
        # ========== FILTRES ==========
        chauffeur_filter = request.GET.get('chauffeur_id', 'tous')
        type_filter = request.GET.get('type_transport', 'tous')
        statut_filter = request.GET.get('statut', 'tous')
        
        # Récupérer les chauffeurs
        if chauffeur_filter != 'tous':
            chauffeurs = Chauffeur.objects.filter(id=chauffeur_filter, actif=True)
        else:
            chauffeurs = Chauffeur.objects.filter(actif=True).order_by('nom')
        
        print(f"👤 {chauffeurs.count()} chauffeur(s) actif(s)")
        
        # ========== STATISTIQUES GLOBALES ==========
        stats_globales = {
            'total_courses': 0,
            'total_revenu': 0.0,
            'total_agents': 0,
            'chauffeurs_actifs': chauffeurs.count()
        }
        
        historique_data = []
        
        for ch in chauffeurs:
            # Base queryset
            courses_query = Course.objects.filter(
                chauffeur=ch,
                date_reelle__gte=date_debut,
                date_reelle__lte=date_fin
            )
            
            # Appliquer les filtres supplémentaires
            if type_filter != 'tous':
                courses_query = courses_query.filter(type_transport=type_filter)
            
            if statut_filter != 'tous':
                courses_query = courses_query.filter(statut=statut_filter)
            
            courses = courses_query.order_by('-date_reelle', '-heure')
            courses_count = courses.count()
            
            # Ignorer les chauffeurs sans courses
            if courses_count == 0:
                continue
                
            revenu = 0.0
            agents = 0
            courses_list = []
            
            for c in courses:
                # Nombre d'agents
                nb_agents = Affectation.objects.filter(course=c).count()
                agents += nb_agents
                
                # Prix de la course
                prix = 0.0
                if hasattr(c, 'prix_total') and c.prix_total:
                    try:
                        prix = float(c.prix_total)
                    except:
                        prix = 0.0
                elif hasattr(c, 'get_prix_course'):
                    try:
                        prix = float(c.get_prix_course() or 0)
                    except:
                        prix = 0.0
                
                # Ajouter au revenu si validée/payée
                if c.statut in ['validee', 'payee']:
                    revenu += prix
                
                courses_list.append({
                    'id': c.id,
                    'date': c.date_reelle.strftime('%Y-%m-%d'),
                    'date_display': c.date_reelle.strftime('%d/%m/%Y'),
                    'type': c.type_transport,
                    'type_display': 'Ramassage' if c.type_transport == 'ramassage' else 'Départ',
                    'heure': c.heure,
                    'heure_display': f"{c.heure}h",
                    'nb_agents': nb_agents,
                    'statut': c.statut,
                    'statut_display': c.get_statut_display() if hasattr(c, 'get_statut_display') else c.statut,
                    'prix': prix,
                    'prix_display': f"{prix:.2f} DNT",
                    'notes': c.notes_validation or ''
                })
            
            # Mettre à jour stats globales
            stats_globales['total_courses'] += courses_count
            stats_globales['total_revenu'] += revenu
            stats_globales['total_agents'] += agents
            
            # Ajouter le chauffeur
            historique_data.append({
                'id': ch.id,
                'nom': ch.nom,
                'telephone': ch.telephone or 'Non spécifié',
                'vehicule': getattr(ch, 'numero_voiture', 'Non spécifié'),
                'type_chauffeur': ch.type_chauffeur or 'standard',
                'actif': ch.actif,
                'super_chauffeur': getattr(ch, 'super_chauffeur', False),
                'statistiques': {
                    'courses_total': courses_count,
                    'revenu_total': round(revenu, 2),
                    'agents_transportes': agents,
                    'moyenne_revenu': round(revenu / courses_count, 2) if courses_count > 0 else 0,
                    'moyenne_agents': round(agents / courses_count, 1) if courses_count > 0 else 0
                },
                'courses': courses_list
            })
            
            print(f"  👤 {ch.nom}: {courses_count} courses, {revenu:.2f} DNT, {agents} agents")
        
        # Moyennes globales
        if stats_globales['total_courses'] > 0:
            stats_globales['moyenne_revenu'] = round(stats_globales['total_revenu'] / stats_globales['total_courses'], 2)
            stats_globales['moyenne_agents'] = round(stats_globales['total_agents'] / stats_globales['total_courses'], 1)
        else:
            stats_globales['moyenne_revenu'] = 0
            stats_globales['moyenne_agents'] = 0
        
        print(f"✅ {len(historique_data)} chauffeur(s) avec courses sur la période")
        print(f"📊 Total: {stats_globales['total_courses']} courses, {stats_globales['total_revenu']:.2f} DNT")
        
        return JsonResponse({
            'success': True,
            'historique': historique_data,
            'stats_globales': stats_globales,
            'filtres': {
                'date_debut': date_debut_str,
                'date_fin': date_fin_str,
                'chauffeur_id': chauffeur_filter,
                'type_transport': type_filter,
                'statut': statut_filter
            },
            'periode': f"{date_debut.strftime('%d/%m/%Y')} - {date_fin.strftime('%d/%m/%Y')}",
            'total_chauffeurs': len(historique_data)
        })
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
@csrf_exempt
@require_GET
def api_super_reservations_demain(request):
    """API pour voir et réserver les agents pour demain - VERSION AVEC GROUPEMENT PAR HEURE"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date, timedelta
        
        from django.apps import apps
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Reservation = apps.get_model('gestion', 'Reservation')
        Agent = apps.get_model('gestion', 'Agent')
        HeureTransport = apps.get_model('gestion', 'HeureTransport')
        
        # Vérifier si c'est un super-chauffeur
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        if not getattr(chauffeur, 'super_chauffeur', False):
            return JsonResponse({
                'success': False,
                'error': 'Accès réservé aux super-chauffeurs'
            }, status=403)
        
        demain = date.today() + timedelta(days=1)
        jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        jour_semaine = jours_fr[demain.weekday()]
        
        print(f"=== SUPER DASHBOARD - Agents pour {demain} ({jour_semaine}) ===")
        
        # 1. Récupérer TOUTES les réservations pour demain
        reservations = Reservation.objects.filter(
            date_reservation=demain,
            statut__in=['reservee', 'confirmee']
        ).select_related('chauffeur', 'agent', 'heure_transport')
        
        print(f"📊 Réservations: {reservations.count()}")
        
        # 2. Récupérer toutes les heures de transport actives
        heures_ramassage = HeureTransport.objects.filter(
            type_transport='ramassage',
            active=True
        ).order_by('ordre', 'heure')
        
        heures_depart = HeureTransport.objects.filter(
            type_transport='depart',
            active=True
        ).order_by('ordre', 'heure')
        
        print(f"⏰ Heures configurées: {heures_ramassage.count()} ramassage, {heures_depart.count()} départ")
        print(f"   Ramassage: {[h.heure for h in heures_ramassage]}")
        print(f"   Départ: {[h.heure for h in heures_depart]}")
        
        # 3. Charger le planning
        try:
            from gestion.utils import GestionnaireTransport
            
            gestionnaire = GestionnaireTransport(request=request)
            
            # Charger le planning depuis la session
            if not gestionnaire.recharger_planning_depuis_session():
                print("⚠️ Planning non chargé dans la session")
                return JsonResponse({
                    'success': False,
                    'error': "Planning non chargé. Veuillez d'abord charger le planning EMS.xlsx",
                    'redirect_to_upload': True
                })
            
            # Vérifier que la date de demain est dans le planning
            dates_par_jour = gestionnaire.dates_par_jour
            date_demain_str = demain.strftime("%d/%m/%Y")
            
            jour_correspondant = None
            for jour_planning, date_planning_str in dates_par_jour.items():
                if date_planning_str == date_demain_str:
                    jour_correspondant = jour_planning
                    print(f"✅ Date trouvée dans planning: {date_demain_str} -> {jour_correspondant}")
                    break
            
            if not jour_correspondant:
                # Essayer de parser les dates pour comparer
                print("⚠️ Date exacte non trouvée, tentative de parsing...")
                for jour_planning, date_planning_str in dates_par_jour.items():
                    try:
                        date_planning = datetime.strptime(date_planning_str, "%d/%m/%Y").date()
                        if date_planning == demain:
                            jour_correspondant = jour_planning
                            print(f"✅ Date correspondante trouvée: {date_planning} -> {jour_correspondant}")
                            break
                    except:
                        continue
            
            if not jour_correspondant:
                print(f"❌ Le planning chargé ne contient pas la date du {date_demain_str}")
                print(f"📅 Dates disponibles dans le planning: {dates_par_jour}")
                
                dates_disponibles = []
                for jour, date_planning in dates_par_jour.items():
                    dates_disponibles.append(f"{jour} : {date_planning}")
                
                return JsonResponse({
                    'success': False,
                    'error': f"Le planning chargé ne contient pas la date du {date_demain_str} ({jour_semaine})",
                    'error_type': 'date_not_in_planning',
                    'date_demandee': date_demain_str,
                    'jour_demande': jour_semaine,
                    'dates_disponibles': dates_disponibles,
                    'redirect_to_upload': True
                })
            
            jour_a_utiliser = jour_correspondant
            print(f"📊 Utilisation du planning pour: {jour_a_utiliser} ({date_demain_str})")
            
        except Exception as e:
            print(f"⚠️ Erreur chargement planning: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Erreur chargement planning: {str(e)}',
                'redirect_to_upload': True
            })
        
        # 4. Récupérer TOUS les chauffeurs pour les options de réservation
        tous_chauffeurs = Chauffeur.objects.filter(actif=True).order_by('nom')
        
        # 5. Préparer les données pour chaque heure - TRAITER CHAQUE HEURE INDIVIDUELLEMENT
        heures_data = []
        
        # A. Traiter les heures de RAMASSAGE
        for heure in heures_ramassage:
            heure_valeur = heure.heure
            print(f"📊 Traitement heure: {heure_valeur}h ({heure.libelle})")
            
            # Créer un filtre pour cette heure spécifique
            class FiltreFormHeure:
                def __init__(self, jour, type_transport, heure_valeur):
                    self.cleaned_data = {
                        'jour': jour,
                        'type_transport': type_transport,
                        'heure_ete': False,
                        'filtre_agents': 'tous'
                    }
                    self.data = {'heure_specifique': str(heure_valeur)}
            
            form_filtre = FiltreFormHeure(jour_a_utiliser, 'ramassage', heure_valeur)
            
            # Obtenir les agents UNIQUEMENT pour cette heure
            liste_transports = gestionnaire.traiter_donnees(form_filtre)
            
            print(f"  📋 {len(liste_transports)} agent(s) trouvé(s) pour {heure_valeur}h")
            
            # Afficher les premiers agents pour déboguer
            if liste_transports:
                print(f"     Exemples: {[t['agent'] for t in liste_transports[:3]]}")
            
            # Préparer la liste des agents pour cette heure
            agents_heure = []
            
            for transport in liste_transports:
                agent_nom = transport['agent']
                agent_adresse = transport.get('adresse', '')
                
                # Chercher l'agent dans la base
                agent_obj = Agent.objects.filter(nom__icontains=agent_nom).first()
                
                if agent_obj:
                    # Vérifier si l'agent est déjà réservé à cette heure
                    reservation_existante = reservations.filter(
                        agent=agent_obj,
                        heure_transport=heure,
                        type_transport='ramassage'
                    ).first()
                    
                    est_reserve = reservation_existante is not None
                    est_mien = est_reserve and reservation_existante.chauffeur_id == int(chauffeur_id)
                    
                    agent_data = {
                        'id': agent_obj.id,
                        'nom': agent_obj.nom,
                        'telephone': agent_obj.telephone or 'Non spécifié',
                        'societe': agent_obj.get_societe_display(),
                        'adresse': agent_adresse or agent_obj.adresse or 'Non spécifiée',
                        'est_complet': agent_obj.est_complet() if hasattr(agent_obj, 'est_complet') else True,
                        'est_reserve': est_reserve,
                        'est_mien': est_mien,
                        'peut_reserver': not est_reserve,
                    }
                    
                    if est_reserve:
                        agent_data['chauffeur_reservant'] = reservation_existante.chauffeur.nom
                        agent_data['chauffeur_reservant_id'] = reservation_existante.chauffeur.id
                        agent_data['reservation_id'] = reservation_existante.id
                    
                    agents_heure.append(agent_data)
            
            # Ajouter les données de cette heure
            heures_data.append({
                'heure_id': heure.id,
                'heure_libelle': heure.libelle,
                'heure_valeur': heure.heure,
                'type_transport': 'ramassage',
                'type_display': 'Ramassage',
                'agents': agents_heure,
                'total_agents': len(agents_heure),
                'agents_reserves': len([a for a in agents_heure if a.get('est_reserve', False)]),
                'agents_disponibles': len([a for a in agents_heure if not a.get('est_reserve', False)]),
            })
        
        # B. Traiter les heures de DÉPART
        for heure in heures_depart:
            heure_valeur = heure.heure
            print(f"📊 Traitement heure: {heure_valeur}h ({heure.libelle})")
            
            # Créer un filtre pour cette heure spécifique
            class FiltreFormHeure:
                def __init__(self, jour, type_transport, heure_valeur):
                    self.cleaned_data = {
                        'jour': jour,
                        'type_transport': type_transport,
                        'heure_ete': False,
                        'filtre_agents': 'tous'
                    }
                    self.data = {'heure_specifique': str(heure_valeur)}
            
            form_filtre = FiltreFormHeure(jour_a_utiliser, 'depart', heure_valeur)
            
            # Obtenir les agents UNIQUEMENT pour cette heure
            liste_transports = gestionnaire.traiter_donnees(form_filtre)
            
            print(f"  📋 {len(liste_transports)} agent(s) trouvé(s) pour {heure_valeur}h")
            
            # Afficher les premiers agents pour déboguer
            if liste_transports:
                print(f"     Exemples: {[t['agent'] for t in liste_transports[:3]]}")
            
            # Préparer la liste des agents pour cette heure
            agents_heure = []
            
            for transport in liste_transports:
                agent_nom = transport['agent']
                agent_adresse = transport.get('adresse', '')
                
                # Chercher l'agent dans la base
                agent_obj = Agent.objects.filter(nom__icontains=agent_nom).first()
                
                if agent_obj:
                    # Vérifier si l'agent est déjà réservé à cette heure
                    reservation_existante = reservations.filter(
                        agent=agent_obj,
                        heure_transport=heure,
                        type_transport='depart'
                    ).first()
                    
                    est_reserve = reservation_existante is not None
                    est_mien = est_reserve and reservation_existante.chauffeur_id == int(chauffeur_id)
                    
                    agent_data = {
                        'id': agent_obj.id,
                        'nom': agent_obj.nom,
                        'telephone': agent_obj.telephone or 'Non spécifié',
                        'societe': agent_obj.get_societe_display(),
                        'adresse': agent_adresse or agent_obj.adresse or 'Non spécifiée',
                        'est_complet': agent_obj.est_complet() if hasattr(agent_obj, 'est_complet') else True,
                        'est_reserve': est_reserve,
                        'est_mien': est_mien,
                        'peut_reserver': not est_reserve,
                    }
                    
                    if est_reserve:
                        agent_data['chauffeur_reservant'] = reservation_existante.chauffeur.nom
                        agent_data['chauffeur_reservant_id'] = reservation_existante.chauffeur.id
                        agent_data['reservation_id'] = reservation_existante.id
                    
                    agents_heure.append(agent_data)
            
            # Ajouter les données de cette heure
            heures_data.append({
                'heure_id': heure.id,
                'heure_libelle': heure.libelle,
                'heure_valeur': heure.heure,
                'type_transport': 'depart',
                'type_display': 'Départ',
                'agents': agents_heure,
                'total_agents': len(agents_heure),
                'agents_reserves': len([a for a in agents_heure if a.get('est_reserve', False)]),
                'agents_disponibles': len([a for a in agents_heure if not a.get('est_reserve', False)]),
            })
        
        # Trier par type puis par heure
        heures_data.sort(key=lambda x: (0 if x['type_transport'] == 'ramassage' else 1, x['heure_valeur']))
        
        # 6. Groupement par chauffeur
        chauffeurs_dict = {}
        for reservation in reservations:
            chauffeur_id_res = reservation.chauffeur.id
            
            if chauffeur_id_res not in chauffeurs_dict:
                chauffeurs_dict[chauffeur_id_res] = {
                    'chauffeur_id': chauffeur_id_res,
                    'chauffeur_nom': reservation.chauffeur.nom,
                    'chauffeur_telephone': reservation.chauffeur.telephone,
                    'total': 0,
                    'ramassage': 0,
                    'depart': 0,
                    'agents': []
                }
            
            chauffeurs_dict[chauffeur_id_res]['total'] += 1
            
            if reservation.type_transport == 'ramassage':
                chauffeurs_dict[chauffeur_id_res]['ramassage'] += 1
            else:
                chauffeurs_dict[chauffeur_id_res]['depart'] += 1
            
            chauffeurs_dict[chauffeur_id_res]['agents'].append({
                'agent_id': reservation.agent.id,
                'agent_nom': reservation.agent.nom,
                'agent_telephone': reservation.agent.telephone or 'Non spécifié',
                'agent_societe': reservation.agent.get_societe_display(),
                'type_transport': reservation.type_transport,
                'type_display': 'Ramassage' if reservation.type_transport == 'ramassage' else 'Départ',
                'heure': reservation.heure_transport.heure,
                'heure_libelle': reservation.heure_transport.libelle,
                'statut': reservation.statut,
                'statut_display': reservation.get_statut_display(),
                'notes': reservation.notes or ''
            })
        
        # 7. Calculer les statistiques globales
        total_agents_programmes = sum(h['total_agents'] for h in heures_data)
        total_reservations = reservations.count()
        total_agents_disponibles = sum(h['agents_disponibles'] for h in heures_data)
        
        print(f"📊 RÉSUMÉ: {total_agents_programmes} agents programmés, {total_reservations} réservations, {total_agents_disponibles} disponibles")
        
        return JsonResponse({
            'success': True,
            'is_super_chauffeur': True,
            'date_demain': demain.strftime('%Y-%m-%d'),
            'date_demain_display': demain.strftime('%d/%m/%Y'),
            'jour_semaine': jour_semaine,
            'jour_correspondant_planning': jour_a_utiliser,
            'date_planning': date_demain_str,
            
            # Données principales - GROUPÉES PAR HEURE
            'heures': heures_data,
            
            # Chauffeurs avec leurs réservations
            'chauffeurs': list(chauffeurs_dict.values()),
            
            # Liste des chauffeurs pour les réservations
            'tous_chauffeurs': [
                {
                    'id': ch.id,
                    'nom': ch.nom,
                    'telephone': ch.telephone,
                    'vehicule': ch.numero_voiture or 'Non spécifié',
                }
                for ch in tous_chauffeurs
            ],
            
            # Super chauffeur actuel
            'super_chauffeur_actuel': {
                'id': chauffeur.id,
                'nom': chauffeur.nom,
                'telephone': chauffeur.telephone,
            },
            
            # Statistiques globales
            'stats': {
                'total_chauffeurs': len(chauffeurs_dict),
                'total_reservations': total_reservations,
                'total_agents_programmes': total_agents_programmes,
                'total_agents_disponibles': total_agents_disponibles,
                'pourcentage_reserves': round((total_reservations / total_agents_programmes * 100) if total_agents_programmes > 0 else 0, 1),
                'heures_ramassage': len([h for h in heures_data if h['type_transport'] == 'ramassage']),
                'heures_depart': len([h for h in heures_data if h['type_transport'] == 'depart']),
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
@csrf_exempt
@require_POST
def api_super_reserver_agent(request):
    """API pour qu'un super-chauffeur réserve un agent (pour lui-même ou pour un autre chauffeur)"""
    super_chauffeur_id = request.session.get('chauffeur_id')
    
    if not super_chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        agent_ids = data.get('agent_ids', [])  # CHANGÉ: Liste d'agents au lieu d'un seul
        chauffeur_id = data.get('chauffeur_id')  # ID du chauffeur pour qui on réserve
        type_transport = data.get('type_transport')
        heure_id = data.get('heure_id')
        notes = data.get('notes', '')
        
        # CHANGÉ: Vérifier si c'est une réservation multiple
        if isinstance(agent_ids, list) and len(agent_ids) > 0:
            is_multiple_reservation = True
        else:
            # Fallback pour compatibilité avec l'ancienne version
            is_multiple_reservation = False
            agent_ids = [data.get('agent_id')] if data.get('agent_id') else []
        
        if not all([agent_ids, chauffeur_id, type_transport, heure_id]):
            return JsonResponse({'success': False, 'error': 'Données manquantes'})
        
        from datetime import date, timedelta
        
        # Récupérer les modèles
        Reservation = apps.get_model('gestion', 'Reservation')
        Agent = apps.get_model('gestion', 'Agent')
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        HeureTransport = apps.get_model('gestion', 'HeureTransport')
        
        # Vérifier si c'est un super-chauffeur
        super_chauffeur = Chauffeur.objects.get(id=super_chauffeur_id)
        
        if not getattr(super_chauffeur, 'super_chauffeur', False):
            return JsonResponse({
                'success': False,
                'error': 'Accès réservé aux super-chauffeurs'
            }, status=403)
        
        # Vérifier que le chauffeur cible existe et est actif
        try:
            chauffeur_cible = Chauffeur.objects.get(id=chauffeur_id, actif=True)
        except Chauffeur.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Chauffeur cible non trouvé ou inactif'})
        
        demain = date.today() + timedelta(days=1)
        heure_transport = HeureTransport.objects.get(id=heure_id)
        
        # Liste pour stocker les résultats
        reservations_created = []
        agents_reserved = []
        
        # Pour chaque agent
        for agent_id in agent_ids:
            # Vérifier si la réservation existe déjà
            reservation_existante = Reservation.objects.filter(
                agent_id=agent_id,
                date_reservation=demain,
                heure_transport_id=heure_id,
                type_transport=type_transport
            ).first()
            
            if reservation_existante:
                if reservation_existante.statut == 'annulee':
                    # Réactiver la réservation annulée
                    reservation_existante.chauffeur_id = chauffeur_id
                    reservation_existante.statut = 'reservee'
                    reservation_existante.notes = f"[Réservé par SUPER {super_chauffeur.nom}] {notes}"
                    reservation_existante.updated_at = timezone.now()
                    reservation_existante.save()
                    
                    reservations_created.append(reservation_existante)
                    agents_reserved.append(reservation_existante.agent)
                    
                elif reservation_existante.statut in ['reservee', 'confirmee']:
                    # Agent déjà réservé - on continue avec les autres
                    continue
            else:
                # Créer une nouvelle réservation
                try:
                    agent = Agent.objects.get(id=agent_id)
                    
                    reservation = Reservation.objects.create(
                        chauffeur_id=chauffeur_id,
                        agent_id=agent_id,
                        date_reservation=demain,
                        type_transport=type_transport,
                        heure_transport_id=heure_id,
                        notes=f"[Réservé par SUPER {super_chauffeur.nom}] {notes}",
                        statut='reservee'
                    )
                    
                    reservations_created.append(reservation)
                    agents_reserved.append(agent)
                    
                except Agent.DoesNotExist:
                    continue  # Agent non trouvé, on continue
        
        # **NOUVEAU: Créer une notification groupée**
        if reservations_created:
            if chauffeur_cible.id != super_chauffeur.id:
                # Super chauffeur réserve pour un autre chauffeur
                create_grouped_super_reservation_notification(
                    chauffeur_cible_id=chauffeur_cible.id,
                    super_chauffeur_nom=super_chauffeur.nom,
                    agents=agents_reserved,
                    heure_transport=heure_transport,
                    type_transport=type_transport,
                    is_multiple_reservation=is_multiple_reservation
                )
            else:
                # Super chauffeur se réserve pour lui-même
                create_self_reservation_notification(
                    super_chauffeur=super_chauffeur,
                    agents=agents_reserved,
                    heure_transport=heure_transport,
                    type_transport=type_transport
                )
        
        return JsonResponse({
            'success': True,
            'message': f'{len(reservations_created)} réservation(s) effectuée(s) pour {chauffeur_cible.nom}',
            'reservations_created': len(reservations_created),
            'agents_count': len(agents_reserved),
            'is_multiple_reservation': is_multiple_reservation
        })
        
    except Exception as e:
        print(f"❌ Erreur api_super_reserver_agent: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
@csrf_exempt
@require_POST
def api_super_annuler_reservation(request, reservation_id):
    """API pour qu'un super-chauffeur annule une réservation - VERSION CORRIGÉE"""
    super_chauffeur_id = request.session.get('chauffeur_id')
    
    if not super_chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date
        
        # Récupérer les modèles
        Reservation = apps.get_model('gestion', 'Reservation')
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        HeureTransport = apps.get_model('gestion', 'HeureTransport')
        
        # Vérifier si c'est un super-chauffeur
        super_chauffeur = Chauffeur.objects.get(id=super_chauffeur_id)
        
        if not getattr(super_chauffeur, 'super_chauffeur', False):
            return JsonResponse({
                'success': False,
                'error': 'Accès réservé aux super-chauffeurs'
            }, status=403)
        
        # Récupérer la réservation
        reservation = Reservation.objects.get(id=reservation_id)
        
        # Vérifier si la réservation est pour demain
        if reservation.date_reservation <= date.today():
            return JsonResponse({
                'success': False,
                'error': 'Cette réservation ne peut plus être annulée (date passée)'
            })
        
        chauffeur_concerne = reservation.chauffeur
        heure_transport = reservation.heure_transport
        
        # **IMPORTANT**: Créer la notification avant d'annuler
        if chauffeur_concerne.id != super_chauffeur.id:
            # Utiliser la fonction importée
            notify_super_annulation(
                chauffeur_cible_id=chauffeur_concerne.id,
                super_chauffeur_nom=super_chauffeur.nom,
                agent_nom=reservation.agent.nom,
                heure_libelle=heure_transport.libelle,
                type_transport=reservation.type_transport
            )
            
        # Annuler la réservation
        reservation.statut = 'annulee'
        reservation.notes = f"[Annulé par SUPER {super_chauffeur.nom}] {reservation.notes}"
        reservation.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Réservation annulée avec succès',
            'reservation_id': reservation.id,
            'agent_id': reservation.agent.id,
            'agent_nom': reservation.agent.nom,
            'chauffeur_concerne_nom': chauffeur_concerne.nom
        })
        
    except Reservation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Réservation non trouvée'})
    except Exception as e:
        print(f"❌ Erreur api_super_annuler_reservation: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
@csrf_exempt
@require_GET
def api_notifications(request):
    """API pour récupérer les notifications d'un chauffeur"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        
        # Récupérer toutes les notifications non lues
        notifications = MobileNotification.objects.filter(
            chauffeur_id=chauffeur_id
        ).order_by('-created_at')[:20]  # Limiter à 20 dernières
        
        notifications_data = []
        for notif in notifications:
            notifications_data.append({
                'id': notif.id,  # ASSUREZ-VOUS QUE L'ID EST INCLUS !
                'type': notif.type_notification,
                'type_display': notif.get_type_notification_display(),
                'message': notif.message,
                'vue': notif.vue,
                'created_at': notif.created_at.strftime('%d/%m/%Y %H:%M'),
                'created_at_iso': notif.created_at.isoformat(),
                'data': notif.data
            })
        
        # Compter les notifications non lues
        unread_count = MobileNotification.objects.filter(
            chauffeur_id=chauffeur_id,
            vue=False
        ).count()
        
        print(f"📨 Notifications pour chauffeur {chauffeur_id}: {unread_count} non lue(s), total: {len(notifications_data)}")
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': unread_count,
            'total': len(notifications_data)
        })
        
    except Exception as e:
        print(f"❌ Erreur api_notifications: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e)
        })
@csrf_exempt
@require_POST
def api_notification_mark_read(request, notification_id):
    """API pour marquer une notification comme lue"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        
        notification = MobileNotification.objects.get(id=notification_id, chauffeur_id=chauffeur_id)
        
        if notification.vue:
            return JsonResponse({
                'success': True,
                'message': 'Notification déjà lue',
                'already_read': True
            })
        
        notification.vue = True
        notification.save()
        
        print(f"✅ Notification {notification_id} marquée comme lue pour chauffeur {chauffeur_id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marquée comme lue',
            'notification_id': notification_id,
            'vue': True
        })
        
    except MobileNotification.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Notification non trouvée'
        })
    except Exception as e:
        print(f"❌ Erreur api_notification_mark_read: {e}")
        return JsonResponse({
            'success': False, 
            'error': str(e)
        })
@csrf_exempt
@require_POST
def api_notifications_mark_all_read(request):
    """API pour marquer toutes les notifications comme lues"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        
        # CORRECTION : Récupérer d'abord le nombre avant de mettre à jour
        notifications = MobileNotification.objects.filter(
            chauffeur_id=chauffeur_id,
            vue=False
        )
        count_before = notifications.count()
        
        # Mettre à jour
        updated = notifications.update(vue=True)
        
        print(f"✅ {updated} notification(s) marquée(s) comme lue(s) pour chauffeur {chauffeur_id}")
        
        return JsonResponse({
            'success': True,
            'message': f'{updated} notification(s) marquée(s) comme lue(s)',
            'count': updated
        })
        
    except Exception as e:
        print(f"❌ Erreur api_notifications_mark_all_read: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e)
        })
@csrf_exempt
@require_GET
def api_notifications_grouped(request):
    """API pour récupérer les notifications groupées par heure"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        
        # Récupérer toutes les notifications non lues groupées
        notifications = MobileNotification.objects.filter(
            chauffeur_id=chauffeur_id,
            vue=False
        ).exclude(
            groupe_notification=''  # Exclure celles sans groupement
        ).select_related('heure_transport').order_by('-date_transport', 'heure_transport__heure', '-created_at')
        
        # Grouper par heure de transport
        grouped_notifications = {}
        
        for notif in notifications:
            key = notif.groupe_notification or f"{notif.date_transport}_{notif.type_transport}"
            
            if key not in grouped_notifications:
                # Créer l'entrée pour ce groupe
                heure_info = "Non spécifiée"
                if notif.heure_transport:
                    heure_info = notif.heure_transport.libelle
                
                date_info = "Non spécifiée"
                if notif.date_transport:
                    date_info = notif.date_transport.strftime('%d/%m/%Y')
                
                grouped_notifications[key] = {
                    'groupe_key': key,
                    'heure_transport_id': notif.heure_transport.id if notif.heure_transport else None,
                    'heure_libelle': heure_info,
                    'date_transport': date_info,
                    'type_transport': notif.type_transport,
                    'type_transport_display': 'Ramassage' if notif.type_transport == 'ramassage' else 'Départ',
                    'notifications': [],
                    'agents': [],  # Liste des agents à transporter
                    'count': 0,
                    'created_at': notif.created_at.isoformat(),
                }
            
            # Ajouter la notification au groupe
            grouped_notifications[key]['notifications'].append({
                'id': notif.id,
                'type': notif.type_notification,
                'type_display': notif.get_type_notification_display(),
                'message': notif.message,
                'data': notif.data,
                'created_at': notif.created_at.strftime('%d/%m/%Y %H:%M'),
            })
            
            # Extraire les informations d'agent si disponibles
            if notif.type_notification == 'agent_selection' and 'agent_nom' in notif.data:
                agent_info = {
                    'nom': notif.data.get('agent_nom'),
                    'adresse': notif.data.get('agent_adresse', ''),
                    'telephone': notif.data.get('agent_telephone', ''),
                }
                if agent_info not in grouped_notifications[key]['agents']:
                    grouped_notifications[key]['agents'].append(agent_info)
            
            grouped_notifications[key]['count'] += 1
        
        # Convertir en liste et trier
        grouped_list = list(grouped_notifications.values())
        grouped_list.sort(key=lambda x: (
            x['date_transport'] if x['date_transport'] != 'Non spécifiée' else '9999-99-99',
            x.get('heure_transport_id', 0)
        ), reverse=True)
        
        # Compter les notifications non groupées (classiques)
        ungrouped_count = MobileNotification.objects.filter(
            chauffeur_id=chauffeur_id,
            vue=False,
            groupe_notification=''
        ).count()
        
        total_unread = MobileNotification.objects.filter(
            chauffeur_id=chauffeur_id,
            vue=False
        ).count()
        
        return JsonResponse({
            'success': True,
            'grouped_notifications': grouped_list,
            'stats': {
                'total_unread': total_unread,
                'grouped_count': len(grouped_list),
                'ungrouped_count': ungrouped_count,
                'total_groups': len(grouped_list),
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur api_notifications_grouped: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e)
        })

@csrf_exempt
@require_POST
def api_notification_group_mark_read(request):
    """API pour marquer tout un groupe de notifications comme lues"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        groupe_key = data.get('groupe_key')
        
        if not groupe_key:
            return JsonResponse({'success': False, 'error': 'Groupe non spécifié'})
        
        MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        
        # Marquer toutes les notifications du groupe comme lues
        updated = MobileNotification.objects.filter(
            chauffeur_id=chauffeur_id,
            groupe_notification=groupe_key,
            vue=False
        ).update(vue=True)
        
        print(f"✅ {updated} notification(s) du groupe '{groupe_key}' marquée(s) comme lue(s)")
        
        return JsonResponse({
            'success': True,
            'message': f'{updated} notification(s) marquée(s) comme lue(s)',
            'updated_count': updated
        })
        
    except Exception as e:
        print(f"❌ Erreur api_notification_group_mark_read: {e}")
        return JsonResponse({
            'success': False, 
            'error': str(e)
        })
# ============================================
# FONCTIONS DE NOTIFICATION AVEC GROUPEMENT
# ============================================


def notify_transport_confirmation(chauffeur_id, nb_agents, heure_libelle, 
                                  type_transport, heure_transport_id, date_transport):
    """
    Notifier la confirmation d'un transport groupé
    """
    message = f"✅ {nb_agents} agent(s) à transporter à {heure_libelle}"
    
    data = {
        'nb_agents': nb_agents,
        'heure_libelle': heure_libelle,
        'type_transport': type_transport,
        'action': 'confirmation',
        'heure_transport_id': heure_transport_id,
        'date_transport': date_transport.isoformat() if date_transport else None,
        'agents_list': []  # Liste des agents à remplir
    }
    
    return create_grouped_notification(
        chauffeur_id=chauffeur_id,
        type_notification='transport_confirmation',
        message=message,
        data=data,
        heure_transport_id=heure_transport_id,
        date_transport=date_transport,
        type_transport=type_transport
    )
@csrf_exempt
@require_GET
def mobile_super_historique_view(request):
    """Page web pour l'historique global"""
    return render(request, 'chauffeurs_mobile/super_historique.html')
# ============================================
# NOTIFICATION DANS LA BASE DE DONNÉES (VISIBLE DANS L'ADMIN)
# ============================================
def notify_admin_hors_planning(course, agent, chauffeur, request):
    """
    Crée une notification dans la base de données
    """
    try:
        from django.contrib.auth.models import User
        from django.utils import timezone
        from gestion.models import Notification  # À créer
        
        # Récupérer l'admin (premier superuser)
        admin = User.objects.filter(is_superuser=True).first()
        
        if not admin:
            print("❌ Aucun admin trouvé dans la base")
            return False
        
        # Créer la notification
        notification = Notification.objects.create(
            utilisateur=admin,
            titre=f"🚨 Agent hors planning - {agent.nom}",
            message=f"L'agent {agent.nom} a été transporté par {chauffeur.nom} le {course.date_reelle} à {course.heure}h alors qu'il n'était pas programmé.",
            lien=f"/admin/gestion/course/{course.id}/",
            type='danger',
            date_creation=timezone.now(),
            lu=False
        )
        
        print(f"✅ Notification créée pour l'admin {admin.username}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur création notification: {e}")
        import traceback
        traceback.print_exc()
        return False
# Ajoutez cette fonction utilitaire dans views.py
def est_heure_valide_pour_creation(heure_course, heure_actuelle):
    """
    Vérifie si une heure de course est valide pour la création
    Gestion spéciale pour les horaires 00h-03h (jour suivant)
    """
    # Convertir en entiers
    if isinstance(heure_course, str):
        heure_course = int(heure_course)
    if isinstance(heure_actuelle, str):
        heure_actuelle = int(heure_actuelle)
    
    print(f"🔍 Vérification: Course à {heure_course}h, Actuelle: {heure_actuelle}h")
    
    # CAS SPÉCIAL: Heures de nuit (00h-03h) - appartiennent au jour suivant
    if heure_course < 4:  # 0,1,2,3
        # Pour les heures de nuit, on considère qu'elles sont toujours valides
        # car elles sont pour le lendemain matin
        print(f"  ✅ Heure de nuit {heure_course}h - toujours valide")
        return True
    
    # CAS NORMAL: Heures de jour (6h-23h)
    if heure_course > heure_actuelle:
        print(f"  ✅ Heure future {heure_course}h > {heure_actuelle}h")
        return True
    elif heure_course == heure_actuelle:
        # Pour l'heure actuelle, on peut permettre jusqu'à 30 min de retard
        # mais c'est géré au niveau métier
        print(f"  ⚠️ Heure actuelle {heure_course}h - à vérifier")
        return heure_course >= heure_actuelle
    else:
        print(f"  ❌ Heure passée {heure_course}h < {heure_actuelle}h")
        return False