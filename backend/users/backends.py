from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

class EmailAuthBackend(ModelBackend):
    """
    Custom Authentication Backend para autenticar usando el email.
    
    Sigue el Principio de Responsabilidad Única enfocándose solo en la evaluación por correo electrónico.
    Si el usuario no existe por email, retorna None permitiendo que Django delege la autenticación 
    al ModelBackend original (Fallback seguro).
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        try:
             # Buscamos al usuario estrictamente por email
             user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
             # Fallo Seguro: Delegar la tarea al siguiente backend configurado (ModelBackend)
             return None
        except UserModel.MultipleObjectsReturned:
             # Preventivo en caso de emails duplicados en la base de datos
             user = UserModel.objects.filter(email=username).order_by('id').first()
             
        if user.check_password(password) and self.user_can_authenticate(user):
             return user
             
        return None
