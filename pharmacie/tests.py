from django.contrib import admin
from django.test import TestCase
from django.test import RequestFactory
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from datetime import timedelta
from .forms import BootstrapAuthenticationForm, UtilisateurCreationForm
from .models import *
from .services import effectuer_vente
class PharmaGestTests(TestCase):
 def setUp(self):
  self.user=Utilisateur.objects.create_user(username='caissier',password='testpass123',role='CAISSIER')
  self.cat=Categorie.objects.create(nom='Antalgiques')
  self.med=Medicament.objects.create(nom='Paracetamol',categorie=self.cat,prix_achat=100,prix_vente=200,seuil_alerte=2)
  self.lot=LotStock.objects.create(medicament=self.med,numero_lot='LOT1',date_peremption=timezone.localdate()+timedelta(days=180),quantite=10)
 def test_stock_disponible(self): self.assertEqual(self.med.stock_disponible,10)
 def test_vente_debite_stock_une_fois(self):
  vente=effectuer_vente(self.user,[{'medicament_id':self.med.pk,'quantite':3}])
  self.lot.refresh_from_db(); self.assertEqual(self.lot.quantite,7); self.assertEqual(vente.total,600)
 def test_refus_stock_insuffisant(self):
  with self.assertRaises(ValidationError): effectuer_vente(self.user,[{'medicament_id':self.med.pk,'quantite':11}])
 def test_lot_perime_non_vendu(self):
  self.lot.date_peremption=timezone.localdate()-timedelta(days=1); self.lot.save()
  with self.assertRaises(ValidationError): effectuer_vente(self.user,[{'medicament_id':self.med.pk,'quantite':1}])
 def test_dashboard_chart_shows_valid_sales_for_period(self):
  effectuer_vente(self.user,[{'medicament_id':self.med.pk,'quantite':2}])
  vente_annulee=Vente.objects.create(numero='V-ANNULEE',caissier=self.user,statut='ANNULEE')
  LigneVente.objects.create(vente=vente_annulee,medicament=self.med,lot=self.lot,quantite=5,prix_unitaire=200)
  self.client.force_login(self.user)

  response=self.client.get('/')

  self.assertEqual(response.status_code,200)
  self.assertEqual(response.context['chart_labels'],['Paracetamol'])
  self.assertEqual(response.context['chart_values'],[2])
  self.assertContains(response,'Répartition des ventes')
 def test_user_creation_form_uses_bootstrap_controls(self):
  form=UtilisateurCreationForm()

  self.assertEqual(form.fields['username'].widget.attrs['class'],'form-control')
  self.assertEqual(form.fields['password1'].widget.attrs['class'],'form-control')
  self.assertEqual(form.fields['role'].widget.attrs['class'],'form-select')
 def test_login_form_uses_bootstrap_controls(self):
  form=BootstrapAuthenticationForm()

  self.assertEqual(form.fields['username'].widget.attrs['class'],'form-control')
  self.assertEqual(form.fields['password'].widget.attrs['class'],'form-control')
 def test_admin_can_supervise_records_without_changing_sales(self):
  vente=effectuer_vente(self.user,[{'medicament_id':self.med.pk,'quantite':1}])
  admin_user=Utilisateur.objects.create_superuser(username='supervision',password='testpass123',role='ADMIN')
  self.client.force_login(admin_user)

  for model_name in ('vente','client','lotstock','mouvementstock','paiement','journalaudit'):
   response=self.client.get(reverse(f'admin:pharmacie_{model_name}_changelist'))
   self.assertEqual(response.status_code,200)

  response=self.client.get(reverse('admin:pharmacie_vente_change',args=[vente.pk]))
  self.assertEqual(response.status_code,200)
  self.assertContains(response,'Paracetamol')
  request=RequestFactory().get('/admin-django/')
  request.user=admin_user
  vente_admin=admin.site._registry[Vente]
  self.assertFalse(vente_admin.has_add_permission(request))
  self.assertFalse(vente_admin.has_delete_permission(request,vente))
