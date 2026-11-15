from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from pharmacie.models import *
class Command(BaseCommand):
 help='Crée un compte administrateur et des données de démonstration.'
 def handle(self,*args,**opts):
  U=get_user_model()
  if not U.objects.filter(username='admin').exists(): U.objects.create_superuser('admin','admin@pharmagest.local','Admin12345',role='ADMIN')
  cat,_=Categorie.objects.get_or_create(nom='Antalgiques')
  cat2,_=Categorie.objects.get_or_create(nom='Vitamines')
  fournisseur,_=Fournisseur.objects.get_or_create(nom='Grossiste Santé Mada',defaults={'telephone':'0340000000','email':'contact@example.mg'})
  for name,categorie,pa,pv in [('Paracétamol 500 mg',cat,150,250),('Vitamine C 500 mg',cat2,300,500)]:
   med,_=Medicament.objects.get_or_create(nom=name,categorie=categorie,defaults={'prix_achat':pa,'prix_vente':pv,'seuil_alerte':5})
   LotStock.objects.get_or_create(medicament=med,numero_lot='DEMO-'+str(med.pk),defaults={'date_peremption':timezone.localdate()+timedelta(days=240),'quantite':50})
  self.stdout.write(self.style.SUCCESS('Données de démonstration créées. Identifiants : admin / Admin12345'))
