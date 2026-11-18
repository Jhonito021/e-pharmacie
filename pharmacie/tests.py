from io import StringIO

from django.contrib import admin
from django.core.management import call_command
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
 def test_rapports_affichent_repartition_ventes_achats_paiements_et_stock(self):
  client=Client.objects.create(nom='Client rapports')
  effectuer_vente(self.user,[{'medicament_id':self.med.pk,'quantite':2}],client=client)
  cat_vitamines=Categorie.objects.create(nom='Vitamines')
  vitamine=Medicament.objects.create(
   nom='Vitamine rapports',categorie=cat_vitamines,prix_achat=100,prix_vente=300
  )
  LotStock.objects.create(
   medicament=vitamine,numero_lot='LOT-VITAMINE',
   date_peremption=timezone.localdate()+timedelta(days=180),quantite=5
  )
  effectuer_vente(
   self.user,[{'medicament_id':vitamine.pk,'quantite':1}],
   mode_paiement='MOBILE_MONEY',client=client,reference='REFERENCE-TEST',
  )
  fournisseur=Fournisseur.objects.create(nom='Fournisseur rapports')
  commande=CommandeAchat.objects.create(
   numero='A-RAPPORTS',fournisseur=fournisseur,cree_par=self.user,statut='RECUE'
  )
  LigneAchat.objects.create(
   commande=commande,medicament=self.med,quantite=4,prix_unitaire=100,recue=4
  )
  admin_user=Utilisateur.objects.create_superuser(
   username='admin-rapports',password='testpass123',role='ADMIN'
  )
  self.client.force_login(admin_user)

  response=self.client.get(reverse('rapports'))

  self.assertEqual(response.status_code,200)
  charts={chart['id']:chart['data'] for chart in response.context['charts']}
  self.assertEqual(
   {item['label']:item['value'] for item in charts['sales-category-chart']},
   {'Antalgiques':400,'Vitamines':300},
  )
  self.assertEqual(charts['purchase-supplier-chart'],[{'label':'Fournisseur rapports','value':400}])
  self.assertEqual(
   {item['label']:item['value'] for item in charts['payment-mode-chart']},
   {'Espèces':400,'Mobile money':300},
  )
  self.assertEqual(
   {item['label']:item['value'] for item in charts['stock-category-chart']},
   {'Antalgiques':8,'Vitamines':4},
  )
  self.assertEqual(response.context['total_receptionne'],400)
  self.assertContains(response,'Stock disponible par catégorie')
  date_future=(timezone.localdate()+timedelta(days=1)).isoformat()
  filtered=self.client.get(reverse('rapports'),{'debut':date_future})
  filtered_charts={chart['id']:chart['data'] for chart in filtered.context['charts']}
  self.assertEqual(filtered.context['total'],0)
  self.assertEqual(filtered.context['total_receptionne'],0)
  self.assertEqual(filtered_charts['sales-category-chart'],[])
  self.assertEqual(filtered_charts['purchase-supplier-chart'],[])
 def test_user_creation_form_uses_bootstrap_controls(self):
  form=UtilisateurCreationForm()

  self.assertEqual(form.fields['username'].widget.attrs['class'],'form-control')
  self.assertEqual(form.fields['password1'].widget.attrs['class'],'form-control')
  self.assertEqual(form.fields['role'].widget.attrs['class'],'form-select')
 def test_login_form_uses_bootstrap_controls(self):
  form=BootstrapAuthenticationForm()

  self.assertEqual(form.fields['username'].widget.attrs['class'],'form-control')
  self.assertEqual(form.fields['password'].widget.attrs['class'],'form-control')
 def test_demo_command_populates_data_idempotently(self):
  call_command('creer_donnees_demo',stdout=StringIO())
  first_snapshot=(
   Client.objects.filter(nom__startswith='Client Démo').count(),
   Fournisseur.objects.filter(nom__in=['Grossiste Santé Mada','Pharma Distribution','Laboratoire Central']).count(),
   CommandeAchat.objects.filter(numero__startswith='DEMO-A-').count(),
   Vente.objects.filter(paiements__reference_externe__startswith='DEMO-PAIEMENT-').distinct().count(),
   MouvementStock.objects.count(),
   sum(lot.quantite for lot in LotStock.objects.all()),
  )

  call_command('creer_donnees_demo',stdout=StringIO())
  second_snapshot=(
   Client.objects.filter(nom__startswith='Client Démo').count(),
   Fournisseur.objects.filter(nom__in=['Grossiste Santé Mada','Pharma Distribution','Laboratoire Central']).count(),
   CommandeAchat.objects.filter(numero__startswith='DEMO-A-').count(),
   Vente.objects.filter(paiements__reference_externe__startswith='DEMO-PAIEMENT-').distinct().count(),
   MouvementStock.objects.count(),
   sum(lot.quantite for lot in LotStock.objects.all()),
  )

  self.assertEqual(first_snapshot[:4],(6,3,2,5))
  self.assertEqual(second_snapshot,first_snapshot)
  self.assertEqual(Utilisateur.objects.filter(username__startswith='demo_').count(),4)
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
  request=RequestFactory().get('/admin/')
  request.user=admin_user
  vente_admin=admin.site._registry[Vente]
  self.assertFalse(vente_admin.has_add_permission(request))
  self.assertFalse(vente_admin.has_delete_permission(request,vente))

 def test_medicament_detail_archivage_et_reactivation(self):
  self.user.role='PHARMACIEN'
  self.user.save(update_fields=['role'])
  self.client.force_login(self.user)
  self.assertEqual(self.client.get(reverse('medicaments')).status_code,200)
  detail=self.client.get(reverse('medicament_detail',args=[self.med.pk]))
  self.assertEqual(detail.status_code,200)
  self.assertContains(detail,'Paracetamol')
  self.client.post(reverse('medicament_archiver',args=[self.med.pk]))
  self.med.refresh_from_db()
  self.assertFalse(self.med.actif)
  self.client.post(reverse('medicament_reactiver',args=[self.med.pk]))
  self.med.refresh_from_db()
  self.assertTrue(self.med.actif)

 def test_categories_modifiables_et_suppression_protegee(self):
  self.user.role='PHARMACIEN'
  self.user.save(update_fields=['role'])
  self.client.force_login(self.user)
  self.assertEqual(self.client.get(reverse('categories')).status_code,200)
  self.client.post(reverse('categorie_modifier',args=[self.cat.pk]),{'nom':'Antalgiques modifiés','description':''})
  self.cat.refresh_from_db()
  self.assertEqual(self.cat.nom,'Antalgiques modifiés')
  self.client.post(reverse('categorie_supprimer',args=[self.cat.pk]))
  self.assertTrue(Categorie.objects.filter(pk=self.cat.pk).exists())
  category=Categorie.objects.create(nom='Inutilisée')
  self.client.post(reverse('categorie_supprimer',args=[category.pk]))
  self.assertFalse(Categorie.objects.filter(pk=category.pk).exists())

 def test_clients_et_fournisseurs_detail_et_desactivation(self):
  self.client.force_login(self.user)
  client=Client.objects.create(nom='Client test')
  fournisseur=Fournisseur.objects.create(nom='Fournisseur test')
  self.assertEqual(self.client.get(reverse('clients')).status_code,200)
  self.assertEqual(self.client.get(reverse('client_detail',args=[client.pk])).status_code,200)
  self.assertEqual(self.client.get(reverse('fournisseurs')).status_code,200)
  self.assertEqual(self.client.get(reverse('fournisseur_detail',args=[fournisseur.pk])).status_code,200)
  self.client.post(reverse('client_statut',args=[client.pk]))
  self.client.post(reverse('fournisseur_statut',args=[fournisseur.pk]))
  client.refresh_from_db()
  fournisseur.refresh_from_db()
  self.assertFalse(client.actif)
  self.assertFalse(fournisseur.actif)
  self.assertTrue(Client.objects.filter(pk=client.pk).exists())
  self.assertTrue(Fournisseur.objects.filter(pk=fournisseur.pk).exists())

 def test_vente_consultable_en_detail(self):
  vente=Vente.objects.create(numero='V-DETAIL',caissier=self.user,total=200)
  LigneVente.objects.create(vente=vente,medicament=self.med,lot=self.lot,quantite=1,prix_unitaire=200)
  self.client.force_login(self.user)
  self.assertEqual(self.client.get(reverse('ventes')).status_code,200)
  response=self.client.get(reverse('vente_detail',args=[vente.pk]))
  self.assertEqual(response.status_code,200)
  self.assertContains(response,'V-DETAIL')
  self.assertContains(response,'Paracetamol')

 def test_lignes_achat_editables_uniquement_en_brouillon(self):
  self.user.role='STOCK'
  self.user.save(update_fields=['role'])
  fournisseur=Fournisseur.objects.create(nom='Fournisseur test')
  commande=CommandeAchat.objects.create(numero='A-TEST',fournisseur=fournisseur,cree_par=self.user)
  ligne=LigneAchat.objects.create(commande=commande,medicament=self.med,quantite=2,prix_unitaire=100)
  self.client.force_login(self.user)
  self.assertEqual(self.client.get(reverse('achats')).status_code,200)
  self.assertEqual(self.client.get(reverse('achat_detail',args=[commande.pk])).status_code,200)
  self.client.post(reverse('ligne_achat_modifier',args=[ligne.pk]),{'medicament':self.med.pk,'quantite':3,'prix_unitaire':'120'})
  ligne.refresh_from_db()
  self.assertEqual(ligne.quantite,3)
  self.client.post(reverse('ligne_achat_supprimer',args=[ligne.pk]))
  self.assertFalse(LigneAchat.objects.filter(pk=ligne.pk).exists())
  self.client.post(reverse('achat_annuler',args=[commande.pk]))
  commande.refresh_from_db()
  self.assertEqual(commande.statut,'ANNULEE')

 def test_utilisateurs_modifiables_et_desactivables_sans_suppression(self):
  admin_user=Utilisateur.objects.create_superuser(username='admin-crud',password='testpass123',email='admin@example.com')
  target=Utilisateur.objects.create_user(username='pharmacien',password='testpass123',role='PHARMACIEN')
  self.client.force_login(admin_user)
  self.assertEqual(self.client.get(reverse('utilisateurs')).status_code,200)
  self_response=self.client.post(reverse('utilisateur_modifier',args=[admin_user.pk]),{
   'username':'admin-crud','first_name':'','last_name':'','email':'admin@example.com',
   'role':'CAISSIER','telephone':'',
  })
  self.assertEqual(self_response.status_code,200)
  admin_user.refresh_from_db()
  self.assertTrue(admin_user.is_active)
  response=self.client.post(reverse('utilisateur_modifier',args=[target.pk]),{
   'username':'pharmacien','first_name':'Jean','last_name':'Test','email':'jean@example.com',
   'role':'PHARMACIEN','telephone':'0340000000','is_active':'on',
  })
  self.assertEqual(response.status_code,302)
  target.refresh_from_db()
  self.assertEqual(target.first_name,'Jean')
  self.client.post(reverse('utilisateur_statut',args=[target.pk]))
  target.refresh_from_db()
  self.assertFalse(target.is_active)
