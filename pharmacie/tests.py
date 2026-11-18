from django.contrib import admin
from django.test import Client as DjangoClient, RequestFactory, TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from datetime import timedelta
from .models import *
from .services import effectuer_vente
from .middleware import JournalRequeteMiddleware
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

 def test_requete_http_authentifiee_journalisee_sans_parametres(self):
  self.client.force_login(self.user)
  response=self.client.get('/clients/?secret=ne-pas-journaliser')
  log=JournalRequete.objects.get(chemin='/clients/')
  self.assertEqual(response.status_code,200)
  self.assertEqual(log.utilisateur,self.user)
  self.assertEqual(log.methode,'GET')
  self.assertEqual(log.statut,200)
  self.assertNotIn('secret',log.chemin)
  self.assertGreaterEqual(log.duree_ms,0)

 def test_requete_anonyme_et_redirection_journalisees(self):
  response=self.client.get('/')
  log=JournalRequete.objects.get(chemin='/')
  self.assertEqual(response.status_code,302)
  self.assertIsNone(log.utilisateur)
  self.assertEqual(log.statut,302)

 def test_requete_refusee_par_csrf_journalisee(self):
  response=DjangoClient(enforce_csrf_checks=True).post('/connexion/',{})
  log=JournalRequete.objects.get(chemin='/connexion/')
  self.assertEqual(response.status_code,403)
  self.assertEqual(log.statut,403)

 def test_journal_requetes_visible_en_lecture_seule_dans_admin(self):
  admin_user=Utilisateur.objects.create_superuser(username='admin-test',password='testpass123',email='admin@example.com')
  JournalRequete.objects.create(methode='GET',chemin='/exemple/',statut=200,duree_ms=3)
  vente=Vente.objects.create(numero='V-TEST',caissier=self.user,total=200)
  self.client.force_login(admin_user)
  response=self.client.get(reverse('admin:pharmacie_journalrequete_changelist'))
  model_admin=admin.site._registry[JournalRequete]
  vente_admin=admin.site._registry[Vente]
  request=RequestFactory().get('/')
  request.user=admin_user
  self.assertEqual(response.status_code,200)
  self.assertContains(response,'/exemple/')
  self.assertFalse(model_admin.has_add_permission(request))
  self.assertFalse(model_admin.has_delete_permission(request))
  vente_response=self.client.get(reverse('admin:pharmacie_vente_change',args=[vente.pk]))
  self.assertEqual(vente_response.status_code,200)
  self.assertFalse(vente_admin.has_add_permission(request))
  self.assertFalse(vente_admin.has_delete_permission(request))
