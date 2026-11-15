from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin): fieldsets=UserAdmin.fieldsets+(('Profil PharmaGest',{'fields':('role','telephone')}),)
for model in [Categorie,Fournisseur,Client,Medicament,LotStock,CommandeAchat,LigneAchat,ReceptionAchat,LigneReception,MouvementStock,Vente,LigneVente,Paiement,RetourVente,JournalAudit]:
 admin.site.register(model)
