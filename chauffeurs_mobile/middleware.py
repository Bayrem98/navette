from django.utils.deprecation import MiddlewareMixin

from django.utils.deprecation import MiddlewareMixin
from django.contrib.sessions.models import Session
from django.utils import timezone

class MobileSessionMiddleware(MiddlewareMixin):
    
    def process_request(self, request):
        # Si c'est une URL mobile
        if request.path.startswith('/mobile/'):
            # Vérifier si la session existe
            if request.session.session_key:
                try:
                    session = Session.objects.get(
                        session_key=request.session.session_key,
                        expire_date__gt=timezone.now()
                    )
                    session_data = session.get_decoded()
                    
                    # ✅ CORRECTION : Vérifier que c'est une session mobile
                    # Si ce n'est PAS une session mobile, on laisse passer quand même
                    # mais on ne la supprime pas
                    if not session_data.get('is_mobile_session'):
                        print(f"⚠️ Session non-mobile détectée mais préservée")
                        # On ne supprime pas la session
                        
                except Session.DoesNotExist:
                    # Session expirée, on redirige vers login
                    if request.path != '/mobile/login/':
                        print("🔄 Session expirée, redirection vers login")
                        from django.shortcuts import redirect
                        return redirect('/mobile/login/')
            else:
                # Pas de session du tout
                if request.path != '/mobile/login/':
                    print("🔄 Pas de session, redirection vers login")
                    from django.shortcuts import redirect
                    return redirect('/mobile/login/')
    
    def process_response(self, request, response):
        return response
