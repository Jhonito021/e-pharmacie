from django.urls import path
from django.contrib.auth import views as auth_views
from .forms import BootstrapAuthenticationForm
from . import views
urlpatterns=[
 path('connexion/',auth_views.LoginView.as_view(template_name='registration/login.html',form_class=BootstrapAuthenticationForm),name='login'),path('deconnexion/',auth_views.LogoutView.as_view(),name='logout'),
 path('',views.dashboard,name='dashboard'),path('medicaments/',views.liste_medicaments,name='medicaments'),path('medicaments/ajouter/',views.medicament_form,name='medicament_ajouter'),path('medicaments/<int:pk>/modifier/',views.medicament_form,name='medicament_modifier'),path('medicaments/<int:pk>/archiver/',views.archiver_medicament,name='medicament_archiver'),
 path('categories/',views.categories,name='categories'),path('categories/<int:pk>/supprimer/',views.supprimer_categorie,name='categorie_supprimer'),
 path('fournisseurs/',views.fournisseurs,name='fournisseurs'),path('fournisseurs/ajouter/',views.fournisseur_form,name='fournisseur_ajouter'),path('fournisseurs/<int:pk>/modifier/',views.fournisseur_form,name='fournisseur_modifier'),
 path('clients/',views.clients,name='clients'),path('clients/ajouter/',views.client_form,name='client_ajouter'),path('clients/<int:pk>/modifier/',views.client_form,name='client_modifier'),
 path('achats/',views.achats,name='achats'),path('achats/creer/',views.achat_creer,name='achat_creer'),path('achats/<int:pk>/',views.achat_detail,name='achat_detail'),path('achats/<int:pk>/pdf/',views.achat_pdf,name='achat_pdf'),
 path('stock/',views.stock,name='stock'),path('stock/inventaire/',views.inventaire,name='inventaire'),path('caisse/',views.caisse,name='caisse'),path('ventes/',views.ventes,name='ventes'),path('ventes/<int:pk>/retour/',views.retour,name='retour'),path('ventes/<int:pk>/recu.pdf',views.recu_pdf,name='recu_pdf'),
 path('rapports/',views.rapports,name='rapports'),path('rapports/<str:kind>.pdf',views.rapport_pdf,name='rapport_pdf'),path('utilisateurs/',views.utilisateurs,name='utilisateurs'),path('utilisateurs/ajouter/',views.utilisateur_creer,name='utilisateur_creer'),path('journal/',views.audit_logs,name='audit_logs'),
]
