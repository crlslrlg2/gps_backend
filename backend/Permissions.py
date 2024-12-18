from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class IsSafelink(BasePermission):
    
    def has_permission(self, request, view):
        # Admins bypass all permission checks
        
        if request.user.role == 'safelink':
            return True

        # Custom logic if the user is not an admin
        raise PermissionDenied("You do not have the required model permissions.")

class IsAgency(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == 'agency' or request.user.role == 'safelink':
          return True 
        raise PermissionDenied("You do not have the required permissions.")
    
class IsDealerSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == 'dealer_super_admin' or request.user.role == 'agency' or request.user.role == 'safelink':
            # Example permission checks
            return True
        raise PermissionDenied("You do not have the required permissions.")
class IsDealerAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == 'dealer_admin' or request.user.role == 'dealer_super_admin' or request.user.role == 'agency' or request.user.role == 'safelink':
                return True
        raise PermissionDenied("You do not have the required permissions.")
class IsDepartmentUser(BasePermission):
    def has_permission(self, request, view):
        print("You do not have the required permissions")
        if request.user.role == 'department_user' or request.user.role == 'dealer_admin' or request.user.role == 'dealer_super_admin' or request.user.role == 'agency' or request.user.role == 'safelink':
                return True
        raise PermissionDenied("You do not have the required permissions.")
        