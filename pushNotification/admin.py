from django.contrib import admin
from .models import FCMToken

# Custom admin interface for FCMToken
class FCMTokenAdmin(admin.ModelAdmin):
    # Display relevant fields in the list view
    list_display = ('user', 'token','timezone', 'created_at')  # Show user, token, and created_at in the list view
    
    # Allow searching by user email or token
    search_fields = ('user__email', 'token')  # Search by user email and token
    
    # Filter options in the sidebar (optional)
    list_filter = ('created_at',)  # Allow filtering by creation date
    
    # You can also define ordering (optional)
    ordering = ('-created_at',)  # Order by the most recent token creation
    
    # Optional: Define fields to show in the form view
    fields = ('user', 'token','timezone')  # Show user and token fields in the edit form

# Register the FCMToken model with the custom admin interface
admin.site.register(FCMToken, FCMTokenAdmin)




