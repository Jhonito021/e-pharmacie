from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import *
class BootstrapForm(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            if isinstance(field.widget,forms.CheckboxInput): field.widget.attrs['class']='form-check-input'
            else: field.widget.attrs['class']='form-control'
class MedicamentForm(BootstrapForm):
    class Meta: model=Medicament; fields=['nom','denomination_generique','categorie','forme','dosage','laboratoire','code_barres','photo','prix_achat','prix_vente','seuil_alerte','actif']
class CategorieForm(BootstrapForm):
    class Meta: model=Categorie; fields=['nom','description']
class FournisseurForm(BootstrapForm):
    class Meta: model=Fournisseur; fields=['nom','adresse','telephone','email','identifiant_fiscal','contact_principal','actif']
class ClientForm(BootstrapForm):
    class Meta: model=Client; fields=['nom','telephone','email','adresse','actif']
class CommandeAchatForm(BootstrapForm):
    class Meta: model=CommandeAchat; fields=['fournisseur']

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['fournisseur'].queryset=Fournisseur.objects.filter(actif=True)

class LigneAchatForm(BootstrapForm):
    class Meta: model=LigneAchat; fields=['medicament','quantite','prix_unitaire']
class UtilisateurCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta): model=Utilisateur; fields=('username','first_name','last_name','email','role','telephone')
class UtilisateurUpdateForm(BootstrapForm):
    class Meta:
        model=Utilisateur
        fields=('username','first_name','last_name','email','role','telephone','is_active')
