# Module de géolocalisation et optimisation d'itinéraires
# Utilise PositionStack comme principal service de géocodage

import folium
from folium import plugins
from geopy.distance import geodesic
import requests
import json
import os
from datetime import datetime
from django.conf import settings
from math import radians, sin, cos, sqrt, atan2
import numpy as np
import time
from django.core.cache import cache
import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple

class GeolocalisationManager:
    def __init__(self):
        # Configuration API PositionStack
        self.positionstack_api_key = getattr(settings, 'POSITIONSTACK_API_KEY', None)
        
        if not self.positionstack_api_key:
            print("⚠️ ATTENTION: POSITIONSTACK_API_KEY non configurée dans settings.py")
            print("⚠️ Ajoutez: POSITIONSTACK_API_KEY = '88bcabc4997f720becd5cb84b44c7b6e'")
        
        # Configuration OSRM pour le routage
        self.osrm_base_url = getattr(settings, 'OSRM_BASE_URL', 'http://router.project-osrm.org')
        
        # Cache activé ?
        self.cache_enabled = getattr(settings, 'CACHE_GEOCODING', True)
        self.cache_timeout = getattr(settings, 'CACHE_TIMEOUT_GEOCODING', 86400)  # 24h
        
        print(f"Configuration géolocalisation - PositionStack: {'OK' if self.positionstack_api_key else 'KO'}")
    
    def geocode_adresse(self, adresse: str) -> Dict[str, Any]:
   
        adresse_nettoyee = self.nettoyer_adresse(adresse)
     
        if self.cache_enabled:
            cache_key = f"geocode_{hashlib.md5(adresse_nettoyee.encode()).hexdigest()}"
            cached_result = cache.get(cache_key)
            if cached_result:
                print(f"⚡ Cache hit: {adresse_nettoyee[:50]}...")
                return cached_result
    
        print(f"🌍 Géocodage: {adresse_nettoyee[:50]}...")
    
        # ÉTAPE 1: RESPECTER LE RATE LIMITING
        current_time = time.time()
        if hasattr(self, 'last_request_time'):
            time_since_last = current_time - self.last_request_time
            if time_since_last < 1.0:  # 1 seconde minimum entre les requêtes
                delay = 1.0 - time_since_last
                print(f"⏳ Rate limiting: attente de {delay:.2f}s")
                time.sleep(delay)
    
        self.last_request_time = time.time()
    
        # ÉTAPE 2: ESSAYER POSITIONSTACK (avec votre clé)
        if self.positionstack_api_key and self.positionstack_api_key != '88bcabc4997f720becd5cb84b44c7b6e':
            result = self._geocode_positionstack(adresse_nettoyee)
            if result['success']:
                # Mettre en cache
                if self.cache_enabled:
                    cache.set(cache_key, result, self.cache_timeout)
                    print(f"  💾 Mis en cache (PositionStack)")
                return result
    
        # ÉTAPE 3: ESSAYER NOMINATIM (OpenStreetMap - gratuit)
        result = self._geocode_nominatim(adresse_nettoyee)
        if result['success']:
            # Mettre en cache
            if self.cache_enabled:
                cache.set(cache_key, result, self.cache_timeout)
                print(f"  💾 Mis en cache (Nominatim)")
            return result
    
        # ÉTAPE 4: FALLBACK PERSONNALISÉ (quartiers de Sousse)
        result = self._fallback_sousse_quartier(adresse_nettoyee)
        if result['success']:
            # Mettre en cache même si fallback
            if self.cache_enabled:
                cache.set(cache_key, result, self.cache_timeout)
                print(f"  💾 Mis en cache (Fallback quartier)")
            return result
    
        # ÉTAPE 5: FALLBACK AU CENTRE DE SOUSSE
        result = self._fallback_sousse_centre(adresse_nettoyee)
        # Mettre en cache même si fallback
        if self.cache_enabled:
            cache.set(cache_key, result, 86400)  # 24h pour les fallbacks
            print(f"  💾 Mis en cache (Fallback centre)")
    
        return result

    def _geocode_positionstack(self, adresse: str) -> Dict[str, Any]:
    
        try:
           params = {
               'access_key': self.positionstack_api_key,
               'query': adresse,
               'country': 'TN',  # Tunisie
               'region': 'Sousse',
               'limit': 1,
               'output': 'json'
           }
        
           response = requests.get(
               "http://api.positionstack.com/v1/forward",
               params=params,
               timeout=5
           )
        
           if response.status_code == 200:
               data = response.json()
            
               if data.get('data') and len(data['data']) > 0:
                   location = data['data'][0]
                
                   result = {
                       'latitude': float(location['latitude']),
                       'longitude': float(location['longitude']),
                       'adresse_formatee': location.get('label', adresse),
                       'success': True,
                       'source': 'positionstack',
                       'confidence': location.get('confidence', 0),
                       'region': location.get('region', 'Sousse'),
                       'pays': location.get('country', 'Tunisia')
                   }
                
                
                   if self.est_dans_zone_sousse(result['latitude'], result['longitude']):
                       result['dans_zone_sousse'] = True
                       print(f"  ✅ PositionStack: coordonnées valides")
                   else:
                       result['dans_zone_sousse'] = False
                       print(f"  ⚠️  PositionStack: hors de Sousse")
                
                   return result
               else:
                   print(f"  ❌ PositionStack: aucun résultat")
                   return {'success': False}
        
           elif response.status_code == 429:
               print(f"  ⚠️  PositionStack: rate limit atteint (429)")
               return {'success': False, 'rate_limited': True}
        
           else:
               print(f"  ❌ PositionStack: erreur HTTP {response.status_code}")
               return {'success': False}
            
        except requests.exceptions.Timeout:
            print(f"  ⏱️  PositionStack: timeout")
            return {'success': False}
        
        except requests.exceptions.RequestException as e:
            print(f"  ❌ PositionStack: erreur réseau: {e}")
            return {'success': False}

    def _geocode_nominatim(self, adresse: str) -> Dict[str, Any]:
  
        try:
            # Formater l'adresse pour Nominatim
            query = f"{adresse}, Sousse, Tunisie"
            url = "https://nominatim.openstreetmap.org/search"
        
            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'tn',
                'accept-language': 'fr'
            }
        
            headers = {
                'User-Agent': 'GestionTransportApp/1.0 (contact@votreentreprise.com)'
            }
        
            response = requests.get(url, params=params, headers=headers, timeout=5)
        
            if response.status_code == 200:
                data = response.json()
            
                if data and len(data) > 0:
                    location = data[0]
                
                    result = {
                        'latitude': float(location['lat']),
                        'longitude': float(location['lon']),
                        'adresse_formatee': location.get('display_name', adresse),
                        'success': True,
                        'source': 'nominatim',
                        'confidence': 0.8,  # Confidence par défaut
                        'region': 'Sousse',
                        'pays': 'Tunisia'
                    }
                
                    if self.est_dans_zone_sousse(result['latitude'], result['longitude']):
                        result['dans_zone_sousse'] = True
                        print(f"  ✅ Nominatim: coordonnées valides")
                    else:
                        result['dans_zone_sousse'] = False
                        print(f"  ⚠️  Nominatim: hors de Sousse")
                
                    return result
                else:
                    print(f"  ❌ Nominatim: aucun résultat")
                    return {'success': False}
          
            elif response.status_code == 429:
                print(f"  ⚠️  Nominatim: rate limit, on attend 1 seconde...")
                time.sleep(1)
                return {'success': False}
        
            else:
                print(f"  ❌ Nominatim: erreur HTTP {response.status_code}")
                return {'success': False}
            
        except Exception as e:
            print(f"  ❌ Nominatim erreur: {e}")
            return {'success': False}

    def _fallback_sousse_quartier(self, adresse: str) -> Dict[str, Any]:
    
    
        quartiers_sousse = {
            # Quartiers principaux
            'Riadh 1' : (35.8085, 10.5920),
            'Riadh 2' : (35.8110, 10.5880),
            'Riadh 3' : (35.8050, 10.5850),
            'Riadh 4' : (35.8020, 10.5800),
            'Riadh 5' : (35.7980, 10.5750),
            'Riadh El Andalous' : (35.8060, 10.5790),
            'Zouhour 1' : (35.8180, 10.6050),
            'Zouhour 2' : (35.8150, 10.6000),
            'Zouhour 3' : (35.8125, 10.5960),
            'Ghodrane' : (35.8120, 10.6120),
            'El Habib' : (35.8100, 10.6050),
            'Msaken Centre' : (35.7300, 10.5850),
            'Msaken Ennour' : (35.7350, 10.5750),
            'Msaken El Bassatine' : (35.7250, 10.5920),
            'Sahloul 1' : (35.8350, 10.5960),
            'Sahloul 2' : (35.8385, 10.5930),
            'Sahloul 3' : (35.8410, 10.5880),
            'Sahloul 4' : (35.8450, 10.5850),
            'Khezama Est' : (35.8525, 10.6150),
            'Khezama Ouest' : (35.8485, 10.6050),
            'Jawhara' : (35.8256, 10.6084),
            'Médina Sousse' : (35.8275, 10.6392),
            'Boujaafar' : (35.8340, 10.6400),
            'Taffala' : (35.8170, 10.6130),
            'Sidi Abdelhamid' : (35.7950, 10.6350),
            'Hammam Sousse' : (35.8580, 10.5980),
            'Akouda' : (35.8680, 10.5650),
            'Kalaa Kebira' : (35.8660, 10.5360),
            'Kalaa Seghira' : (35.8200, 10.5600),
            'Hergla' : (36.0312, 10.5091),
        }
    
        adresse_lower = adresse.lower()
    
        for quartier, coords in quartiers_sousse.items():
            if quartier in adresse_lower:
                # Ajouter un petit offset aléatoire pour éviter les points superposés
                import random
                offset_lat = random.uniform(-0.003, 0.003)
                offset_lon = random.uniform(-0.003, 0.003)
                
                result = {
                    'latitude': coords[0] + offset_lat,
                    'longitude': coords[1] + offset_lon,
                    'adresse_formatee': f"{adresse} (quartier {quartier})",
                    'success': True,
                    'source': 'fallback_quartier',
                    'confidence': 0.6,
                    'dans_zone_sousse': True,
                    'quartier': quartier
                }
                
                print(f"  🗺️  Fallback quartier: trouvé {quartier}")
                return result
    
        return {'success': False}

    def _fallback_sousse_centre(self, adresse: str) -> Dict[str, Any]:
    
        import random
    
        # Centre de Sousse + dispersion aléatoire
        centre_lat = 35.8256 + random.uniform(-0.02, 0.02)
        centre_lon = 10.6415 + random.uniform(-0.02, 0.02)
    
        result = {
            'latitude': centre_lat,
            'longitude': centre_lon,
            'adresse_formatee': f"{adresse}, Sousse (approximatif)",
            'success': False,  # Note: False car c'est un fallback
            'source': 'fallback_centre',
            'confidence': 0.4,
            'dans_zone_sousse': True
        }
    
        print(f"  📍 Fallback centre: coordonnées approximatives")
        return result
    
    def nettoyer_adresse(self, adresse: str) -> str:
       
        if not adresse:
            return "Sousse, Tunisie"
        
        # Convertir en string et nettoyer
        adresse = str(adresse).strip()
        
        # Supprimer les caractères spéciaux problématiques
        adresse = re.sub(r'[<>\\\'"]', '', adresse)
        
        # Normaliser les séparateurs
        adresse = adresse.replace(';', ',').replace('|', ',').replace('/', ',')
        
        # Supprimer les espaces multiples
        adresse = re.sub(r'\\s+', ' ', adresse)
        
        # Optimisation pour PositionStack - format recommandé
        # PositionStack préfère: [adresse], [ville], [région], [pays]
        
        # Vérifier si déjà formatée
        if 'sousse' in adresse.lower() and 'tunisie' in adresse.lower():
            return adresse
        
        # Ajouter Sousse, Tunisie si manquant
        if 'sousse' not in adresse.lower():
            if 'tunisie' not in adresse.lower():
                adresse = f"{adresse}, Sousse, Tunisie"
            else:
                adresse = f"{adresse}, Sousse"
        
        return adresse
    
    def est_dans_zone_sousse(self, lat: float, lon: float) -> bool:
      
        # Zone Sousse + banlieue
        zone_sousse = {
            'lat_min': 35.65,
            'lat_max': 36.00,
            'lon_min': 10.40,
            'lon_max': 10.90
        }
        
        return (zone_sousse['lat_min'] <= lat <= zone_sousse['lat_max'] and 
                zone_sousse['lon_min'] <= lon <= zone_sousse['lon_max'])
    
    def batch_geocode_adresses(self, adresses_list: List[str]) -> List[Dict[str, Any]]:
       
        print(f"📦 Géocodage batch de {len(adresses_list)} adresses...")
        
        resultats = []
        succes = 0
        echecs = 0
        
        for i, adresse in enumerate(adresses_list):
            print(f"  [{i+1}/{len(adresses_list)}] {adresse[:50]}...")
            
            result = self.geocode_adresse(adresse)
            result['adresse_origine'] = adresse
            
            if result['success']:
                succes += 1
            else:
                echecs += 1
            
            resultats.append(result)
            
            # Respecter les limites d'API (1 requête/seconde)
            if i < len(adresses_list) - 1:
                time.sleep(0.2)  # 200ms entre les requêtes
        
        print(f"✅ Batch terminé: {succes} succès, {echecs} échecs")
        return resultats
    
    def calculer_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        
        try:
            return geodesic(point1, point2).kilometers
        except Exception:
            # Fallback: formule de Haversine
            return self.haversine(point1[0], point1[1], point2[0], point2[1])
    
    def haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
       
        R = 6371  # Rayon terrestre en km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def optimiser_itineraire(self, points: List[Dict[str, Any]], 
                            point_depart_index: Optional[int] = 0) -> Dict[str, Any]:
       
        print(f"🔄 Traitement de {len(points)} points...")
        
        # Si un seul point, retourner directement
        if len(points) < 2:
            print(f"⚠️  Seulement {len(points)} point(s) - pas d'optimisation possible")
            
            # Préparer l'itinéraire pour un seul point
            itineraire_ordonne = []
            for idx, point in enumerate(points):
                itineraire_ordonne.append({
                    **point,
                    'ordre_visite': idx + 1,
                    'index_original': idx
                })
            
            return {
                'itineraire': itineraire_ordonne,
                'ordre_indices': list(range(len(points))),
                'distance_totale': 0,
                'distance_moyenne': 0,
                'distance_max': 0,
                'distance_min': 0,
                'nombre_points': len(points),
                'point_depart': points[0].get('nom', 'Point 1') if points else 'Aucun',
                'point_arrivee': points[-1].get('nom', f'Point {len(points)}') if points else 'Aucun',
                'optimise': False,
                'economie_estimee': 0,
                'temps_estime_minutes': 0
            }
        
        print(f"🔄 Optimisation itinéraire ({len(points)} points)...")
        
        # Créer matrice de distances
        n = len(points)
        distances = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    point1 = (points[i]['latitude'], points[i]['longitude'])
                    point2 = (points[j]['latitude'], points[j]['longitude'])
                    distances[i][j] = self.calculer_distance(point1, point2)
        
        # Algorithme du plus proche voisin
        if point_depart_index is None:
            point_depart_index = 0
        
        visite = [point_depart_index]
        non_visite = list(range(n))
        non_visite.remove(point_depart_index)
        
        # Parcours des points
        while non_visite:
            dernier = visite[-1]
            # Trouver le point le plus proche
            plus_proche = min(non_visite, key=lambda x: distances[dernier][x])
            visite.append(plus_proche)
            non_visite.remove(plus_proche)
        
        # Calcul distance totale
        distance_totale = 0
        for i in range(len(visite)-1):
            distance_totale += distances[visite[i]][visite[i+1]]
        
        # Construire l'itinéraire ordonné
        itineraire_ordonne = []
        for idx in visite:
            point = points[idx]
            itineraire_ordonne.append({
                **point,
                'ordre_visite': len(itineraire_ordonne) + 1,
                'index_original': idx
            })
        
        # Calculer les statistiques
        distances_etapes = []
        for i in range(len(visite)-1):
            distances_etapes.append(distances[visite[i]][visite[i+1]])
        
        # Gérer le cas où il n'y a qu'un seul point ou aucune étape
        if distances_etapes:
            distance_moyenne = np.mean(distances_etapes)
            distance_max = max(distances_etapes)
            distance_min = min(distances_etapes)
        else:
            distance_moyenne = 0
            distance_max = 0
            distance_min = 0
        
        resultat = {
            'itineraire': itineraire_ordonne,
            'ordre_indices': visite,
            'distance_totale': round(distance_totale, 2),
            'distance_moyenne': round(distance_moyenne, 2),
            'distance_max': round(distance_max, 2),
            'distance_min': round(distance_min, 2),
            'nombre_points': n,
            'point_depart': points[visite[0]].get('nom', 'Point 1'),
            'point_arrivee': points[visite[-1]].get('nom', f'Point {n}'),
            'optimise': True if len(points) > 1 else False,
            'economie_estimee': round(distance_totale * 0.15, 2) if len(points) > 1 else 0,
            'temps_estime_minutes': round(distance_totale / 40 * 60, 1) if len(points) > 1 else 0
        }
        
        if len(points) > 1:
            print(f"✅ Itinéraire optimisé: {resultat['distance_totale']} km "
                  f"(économie: {resultat['economie_estimee']} km)")
        else:
            print(f"📍 {len(points)} point(s) affiché(s) sur la carte")
        
        return resultat
    
    def creer_carte_itineraire(self, itineraire: Dict[str, Any], 
                              titre: str = "Itinéraire optimisé",
                              output_dir: str = None) -> Dict[str, Any]:
        
        if not itineraire['itineraire']:
            return {'success': False, 'error': "Aucun point dans l'itinéraire"}
        
        points = itineraire['itineraire']
        
        # Centre de la carte
        latitudes = [p['latitude'] for p in points]
        longitudes = [p['longitude'] for p in points]
        centre_lat = np.mean(latitudes)
        centre_lon = np.mean(longitudes)
        
        # Créer la carte Folium avec tuiles françaises
        m = folium.Map(
            location=[centre_lat, centre_lon],
            zoom_start=12,
            tiles='https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png',
            attr='© OpenStreetMap France',
            control_scale=True
        )        
        # Ajouter les marqueurs
        for i, point in enumerate(points):
            # Popup HTML
            popup_html = f'''
            <div style="width: 220px;">
                <div style="background: #2c3e50; color: white; padding: 6px 10px; border-radius: 4px 4px 0 0;">
                    <strong>#{point.get('ordre_visite', i+1)} - {point.get('nom', 'Point')}</strong>
                </div>
                <div style="padding: 8px;">
                    <p style="margin: 4px 0; font-size: 12px;">
                        <i class="fa fa-map-marker"></i> {point.get('adresse', 'N/A')}
                    </p>
                    <p style="margin: 4px 0; font-size: 12px;">
                        <i class="fa fa-building"></i> {point.get('societe', 'N/A')}
                    </p>
                    <p style="margin: 4px 0; font-size: 12px;">
                        <i class="fa fa-phone"></i> {point.get('telephone', 'N/A')}
                    </p>
                    <hr style="margin: 6px 0;">
                    <p style="margin: 4px 0; font-size: 11px; color: #666;">
                        Lat: {point['latitude']:.5f}<br>
                        Lon: {point['longitude']:.5f}
                    </p>
                </div>
            </div>
            '''
            
            # Couleur du marqueur
            if i == 0:
                color = 'green'
                icon = 'play'
                prefix = 'fa'
                tooltip = f"DÉPART: {point.get('nom', 'Point 1')}"
            elif i == len(points) - 1:
                color = 'red'
                icon = 'flag-checkered'
                prefix = 'fa'
                tooltip = f"ARRIVÉE: {point.get('nom', f'Point {len(points)}')}"
            else:
                color = 'blue'
                icon = 'circle'
                prefix = 'fa'
                tooltip = f"#{i+1}: {point.get('nom', f'Point {i+1}')}"
            
            folium.Marker(
                location=[point['latitude'], point['longitude']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=tooltip,
                icon=folium.Icon(color=color, icon=icon, prefix=prefix)
            ).add_to(m)
        
        # Ligne de l'itinéraire
        coordinates = [[p['latitude'], p['longitude']] for p in points]
        folium.PolyLine(
            coordinates,
            color='#3498db',
            weight=4,
            opacity=0.7,
            dash_array='5, 5',
            popup=f"Itinéraire: {itineraire['distance_totale']} km"
        ).add_to(m)
        
        # Plugins utiles
        plugins.Fullscreen().add_to(m)
        plugins.MeasureControl().add_to(m)
        
        # Légende
        legend_html = f'''
        <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000;
                    background: white; padding: 10px; border-radius: 5px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.2); font-size: 12px;">
            <h4 style="margin: 0 0 8px 0;">{titre}</h4>
            <div>🟢 Départ: {points[0].get('nom', 'Point 1')[:20]}</div>
            <div>🔴 Arrivée: {points[-1].get('nom', f'Point {len(points)}')[:20]}</div>
            <div>🔵 Points: {len(points)}</div>
            <div>📏 Distance: {itineraire['distance_totale']} km</div>
            <div>⏱️ Temps estimé: {itineraire.get('temps_estime_minutes', 0)} min</div>
            <div>💰 Économie: {itineraire.get('economie_estimee', 0)} km</div>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Sauvegarder la carte
        try:
            if output_dir is None:
                # Utiliser MEDIA_ROOT de Django
                media_root = getattr(settings, 'MEDIA_ROOT', 'media')
                output_dir = os.path.join(media_root, 'cartes_itineraire')
            
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"carte_{timestamp}.html"
            filepath = os.path.join(output_dir, filename)
            
            m.save(filepath)
            
            # URL relative pour le web
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            url = f"{media_url}cartes_itineraire/{filename}"
            
            print(f"✅ Carte sauvegardée: {filepath}")
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': filename,
                'url': url,
                'html': m.get_root().render()
            }
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde carte: {e}")
            return {
                'success': False,
                'error': str(e),
                'html': m.get_root().render()  # Retourner le HTML quand même
            }
    
    def generer_rapport_optimisation(self, agents_data: List[Dict[str, Any]], 
                                    jour: str, type_transport: str, heure: str = None) -> Dict[str, Any]:
        
        print(f"📊 Génération rapport optimisation: {jour}, {type_transport}" + 
              (f", heure={heure}" if heure else ""))
        
        # Filtrer les agents par heure si spécifiée - CORRECTION ICI
        agents_filtres = agents_data
        if heure:
            try:
                # Convertir l'heure string en int pour la comparaison
                heure_int = int(heure)
                print(f"🔍 Filtrage par heure '{heure}' (converti en {heure_int})...")
                
                # Filtrer les agents - comparer avec l'heure de l'agent (qui peut être int ou string)
                agents_filtres = []
                for agent in agents_data:
                    agent_heure = agent.get('heure')
                    
                    # Si l'agent a une heure
                    if agent_heure is not None:
                        # Convertir l'heure de l'agent en int pour la comparaison
                        try:
                            if isinstance(agent_heure, str):
                                # Si format "HH:MM", prendre seulement les heures
                                if ':' in agent_heure:
                                    agent_heure_int = int(agent_heure.split(':')[0])
                                else:
                                    agent_heure_int = int(agent_heure)
                            else:
                                agent_heure_int = int(agent_heure)
                            
                            # Comparer les heures
                            if agent_heure_int == heure_int:
                                agents_filtres.append(agent)
                        except (ValueError, TypeError):
                            # Si conversion échoue, comparer comme string
                            if str(agent_heure) == str(heure):
                                agents_filtres.append(agent)
                
                print(f"🔍 Filtrage par heure '{heure}': {len(agents_filtres)} agents sur {len(agents_data)}")
                
            except ValueError:
                print(f"⚠️  Heure invalide: {heure}, pas de filtrage")
                agents_filtres = agents_data
        
        # Géocoder les adresses des agents
        adresses = [agent.get('adresse', '') for agent in agents_filtres]
        geocodes = self.batch_geocode_adresses(adresses)
        
        # Combiner avec les données agents
        points = []
        for i, (agent, geocode) in enumerate(zip(agents_filtres, geocodes)):
            point = {
                'nom': agent.get('nom', f'Agent {i+1}'),
                'adresse': agent.get('adresse', ''),
                'latitude': geocode['latitude'],
                'longitude': geocode['longitude'],
                'societe': agent.get('societe', ''),
                'telephone': agent.get('telephone', ''),
                'agent_id': agent.get('id'),
                'geocode_success': geocode['success'],
                'geocode_source': geocode['source'],
                'heure': agent.get('heure', heure)  # Ajouter l'heure au point
            }
            points.append(point)
        
        # Optimiser l'itinéraire
        itineraire_optimise = self.optimiser_itineraire(points)
        
        # Créer la carte
        titre_carte = f"Itinéraire {type_transport} - {jour}"
        if heure:
            titre_carte += f" - {heure}"
        carte_resultat = self.creer_carte_itineraire(itineraire_optimise, titre_carte)
        
        # Générer le rapport
        rapport = {
            'meta': {
                'date_generation': datetime.now().isoformat(),
                'jour': jour,
                'type_transport': type_transport,
                'heure': heure,
                'nombre_agents': len(agents_filtres),
                'nombre_agents_total': len(agents_data)
            },
            'statistiques': {
                'distance_totale_km': itineraire_optimise['distance_totale'],
                'distance_moyenne_km': itineraire_optimise['distance_moyenne'],
                'economie_estimee_km': itineraire_optimise['economie_estimee'],
                'temps_estime_minutes': itineraire_optimise['temps_estime_minutes'],
                'geocodage_reussite': len([p for p in points if p['geocode_success']]),
                'geocodage_echec': len([p for p in points if not p['geocode_success']])
            },
            'itineraire': itineraire_optimise['itineraire'],
            'visualisation': {
                'carte_url': carte_resultat.get('url') if carte_resultat['success'] else None,
                'carte_fichier': carte_resultat.get('filepath') if carte_resultat['success'] else None
            },
            'points_details': points
        }
        
        print(f"✅ Rapport généré: {len(agents_filtres)} agents" + 
              (f" (filtre: {heure})" if heure else "") + 
              f", {itineraire_optimise['distance_totale']} km")
        
        return rapport    
    def obtenir_temps_trajet_estime(self, point1: Tuple[float, float], 
                                   point2: Tuple[float, float], 
                                   mode: str = 'driving') -> Dict[str, Any]:
       
        try:
            # Utiliser OSRM pour une estimation précise
            url = f"{self.osrm_base_url}/route/v1/{mode}/{point1[1]},{point1[0]};{point2[1]},{point2[0]}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 'Ok':
                    route = data['routes'][0]
                    return {
                        'duree_secondes': route['duration'],
                        'duree_minutes': round(route['duration'] / 60, 1),
                        'distance_metres': route['distance'],
                        'distance_km': round(route['distance'] / 1000, 2),
                        'source': 'osrm'
                    }
        except:
            pass
        
        # Fallback: estimation simple (40 km/h en moyenne)
        distance_km = self.calculer_distance(point1, point2)
        vitesse_moyenne = 40  # km/h
        duree_heures = distance_km / vitesse_moyenne
        
        return {
            'duree_secondes': duree_heures * 3600,
            'duree_minutes': round(duree_heures * 60, 1),
            'distance_metres': distance_km * 1000,
            'distance_km': round(distance_km, 2),
            'source': 'estimation'
        }

# Singleton pour l'utilisation globale
geolocalisation_manager = GeolocalisationManager()

# Fonctions d'export pour Django
def geocoder_adresse(adresse: str) -> Dict[str, Any]:
    return geolocalisation_manager.geocode_adresse(adresse)

def optimiser_itineraire_agents(agents_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    return geolocalisation_manager.optimiser_itineraire(agents_data)

def generer_rapport_transport(agents_data: List[Dict[str, Any]], 
                         jour: str, type_transport: str) -> Dict[str, Any]:
    return geolocalisation_manager.generer_rapport_optimisation(agents_data, jour, type_transport)
