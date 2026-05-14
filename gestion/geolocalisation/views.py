# Vues pour la géolocalisation
from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta
import os

from .utils import GeolocalisationManager
from gestion.models import Agent, Affectation, Course
from gestion.utils import GestionnaireTransport

@login_required
def visualiser_carte(request):
    
    context = {
        'page_title': 'Carte Interactive',
        'active_tab': 'carte',
    }
    return render(request, 'gestion/carte.html', context)

@login_required
@csrf_exempt
def optimiser_itineraire(request):
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            jour = data.get('jour')
            type_transport = data.get('type_transport')
            heure_str = data.get('heure')  # Chaîne de caractères
            
            if not all([jour, type_transport, heure_str]):
                return JsonResponse({'success': False, 'error': 'Donnees manquantes'})
            
            # Convertir l'heure en entier pour la comparaison
            try:
                # Si l'heure est au format "HH:MM", extraire les heures
                if ':' in heure_str:
                    heure_int = int(heure_str.split(':')[0])
                else:
                    heure_int = int(heure_str)
            except:
                heure_int = None
            
            # Charger les agents du planning
            gestionnaire = GestionnaireTransport()
            if not gestionnaire.recharger_planning_depuis_session():
                return JsonResponse({'success': False, 'error': 'Planning non charge'})
            
            gestionnaire.dates_par_jour = request.session.get('gestionnaire_dates', {})
            
            # Créer un faux formulaire de filtre
            class FiltreForm:
                def __init__(self, jour, type_transport, heure_int):
                    self.cleaned_data = {
                        'jour': jour,
                        'type_transport': type_transport,
                        'heure_ete': False,
                        'filtre_agents': 'tous'
                    }
                    # Ajouter l'heure pour traiter_donnees
                    self.data = {'heure_specifique': str(heure_int)} if heure_int else {}
            
            form_filtre = FiltreForm(jour, type_transport, heure_int)
            liste_transports = gestionnaire.traiter_donnees(form_filtre)
            
            if not liste_transports:
                return JsonResponse({
                    'success': False, 
                    'error': f'Aucun agent trouve pour {jour} {type_transport} à {heure_str}'
                })
            
            # Géocoder les adresses
            geo_manager = GeolocalisationManager()
            agents_avec_coords = []
            
            for transport in liste_transports:
                # L'heure de l'agent est déjà filtrée par traiter_donnees
                # Donc tous les agents ici correspondent à l'heure
                
                # Géocoder l'adresse
                result_geo = geo_manager.geocode_adresse(transport['adresse'])
                
                agent_data = {
                    'nom': transport['agent'],  # Changé de 'agent' à 'nom'
                    'adresse': transport['adresse'],
                    'latitude': result_geo['latitude'],
                    'longitude': result_geo['longitude'],
                    'societe': transport['societe'],
                    'telephone': transport['telephone'],
                    'heure': transport['heure'],  # Garder comme entier
                    'geocode_success': result_geo['success'],
                    'adresse_formatee': result_geo.get('adresse_formatee', transport['adresse']),
                    'id': transport.get('agent_id')
                }
                agents_avec_coords.append(agent_data)
            
            # Optimiser l'itinéraire avec l'heure
            rapport = geo_manager.generer_rapport_optimisation(
                agents_avec_coords,
                jour,
                type_transport,
                heure_str  # Passer la chaîne pour l'affichage
            )
            
            if rapport:
                # Sauvegarder dans la session pour réutilisation
                request.session['dernier_itineraire'] = rapport
                
                return JsonResponse({
                    'success': True,
                    'rapport': rapport
                })
            else:
                return JsonResponse({'success': False, 'error': 'Erreur optimisation'})
                
        except Exception as e:
            print(f"❌ Erreur optimisation: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Methode non autorisee'})

@login_required
@csrf_exempt
def geocoder_adresses(request):
   
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            adresses = data.get('adresses', [])
            
            if not adresses:
                return JsonResponse({'success': False, 'error': 'Aucune adresse fournie'})
            
            geo_manager = GeolocalisationManager()
            resultats = geo_manager.batch_geocode_adresses(adresses)
            
            statistiques = {
                'total': len(resultats),
                'reussis': sum(1 for r in resultats if r['success']),
                'echecs': sum(1 for r in resultats if not r['success'])
            }
            
            return JsonResponse({
                'success': True,
                'resultats': resultats,
                'statistiques': statistiques
            })
             
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Methode non autorisée'})

@login_required
def rapport_optimisation(request):
    "Page de rapport d'optimisation"
    dernier_rapport = request.session.get('dernier_itineraire', None)
    
    context = {
        'page_title': "Rapport d'Optimisation",
        'active_tab': 'rapport',
        'dernier_rapport': dernier_rapport
    }
    return render(request, 'gestion/rapport_optimisation.html', context)

@login_required
def statistiques_geolocalisation(request):
    
    agents_total = Agent.objects.count()
    agents_avec_adresse = Agent.objects.exclude(
        adresse__in=['', 'Adresse a completer']
    ).count()
    
    context = {
        'page_title': 'Statistiques Geolocalisation',
        'active_tab': 'stats',
        'agents_total': agents_total,
        'agents_avec_adresse': agents_avec_adresse,
        'taux_adresses': round((agents_avec_adresse / agents_total * 100), 1) if agents_total > 0 else 0,
    }
    return render(request, 'gestion/statistiques_geo.html', context)
