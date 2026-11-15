from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

def roles(*allowed):
 def decorator(view):
  @wraps(view)
  def wrapped(request,*args,**kwargs):
   if not request.user.is_authenticated: return redirect('login')
   if request.user.is_superuser or request.user.role in allowed: return view(request,*args,**kwargs)
   raise PermissionDenied('Vous ne disposez pas des permissions nécessaires.')
  return wrapped
 return decorator
