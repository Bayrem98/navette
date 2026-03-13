from django.contrib import admin
from .models import MobileNotification, MobileCourseStatus

@admin.register(MobileNotification)
class MobileNotificationAdmin(admin.ModelAdmin):
    list_display = ['chauffeur', 'type_notification', 'message_short', 'vue', 'created_at']
    list_filter = ['type_notification', 'vue', 'created_at']
    search_fields = ['chauffeur__nom', 'message']
    
    def message_short(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_short.short_description = 'Message'

@admin.register(MobileCourseStatus)
class MobileCourseStatusAdmin(admin.ModelAdmin):
    list_display = ['course', 'chauffeur', 'statut_mobile', 'heure_reelle', 'created_at']
    list_filter = ['statut_mobile', 'created_at']
    search_fields = ['course__id', 'chauffeur__nom']
