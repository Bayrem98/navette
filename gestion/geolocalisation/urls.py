# URLs pour la géolocalisation
from django.urls import path
from . import views
urlpatterns = [
    path('carte/', views.visualiser_carte, name='carte'),
    path('optimiser/', views.optimiser_itineraire, name='optimiser_itineraire'),
    path('geocoder/', views.geocoder_adresses, name='geocoder_adresses'),
    path('rapport/', views.rapport_optimisation, name='rapport_optimisation'),
    path('statistiques/', views.statistiques_geolocalisation, name='statistiques_geolocalisation'),
]
