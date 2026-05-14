from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from gestion import views as gestion_views  # IMPORTANT: ajouter cet import

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='gestion/login.html'), name='login'),
    path('logout/', gestion_views.admin_logout_view, name='logout'),
    path('', include('gestion.urls')),
    path('geolocalisation/', include('gestion.geolocalisation.urls')),
    path('mobile/', include('chauffeurs_mobile.urls')),
    path('gestion/valider-course/<int:course_id>/', include('gestion.urls'), name='valider_course_admin'),
    path('gestion/refuser-course/<int:course_id>/', include('gestion.urls'), name='refuser_course_admin'),
    path('api/corriger_coordonnees/', gestion_views.corriger_coordonnees_agent, name='corriger_coordonnees'),
           
    # Validation des courses
    path('chauffeurs/api/demander_validation/<int:course_id>/', 
         gestion_views.demander_validation_course, name='demander_validation_course'),
    path('chauffeurs/api/course/<int:course_id>/', 
         gestion_views.get_course_details, name='get_course_details'),
    path('chauffeurs/api/modifier_course/<int:course_id>/', 
         gestion_views.modifier_course, name='modifier_course'),
    
    # Validation admin (pour les administrateurs)
    path('validation/valider-course/<int:course_id>/', 
         gestion_views.valider_course_admin, name='valider_course_admin'),
    path('validation/refuser-course/<int:course_id>/', 
         gestion_views.refuser_course_admin, name='refuser_course_admin'),
    path('validation/courses-attente/', 
         gestion_views.courses_en_attente_validation, name='courses_en_attente_validation'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
