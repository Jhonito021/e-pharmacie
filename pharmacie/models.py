from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal

class Utilisateur(AbstractUser):
    ROLE_CHOICES=[('ADMIN','Administrateur'),('PHARMACIEN','Pharmacien responsable'),('STOCK','Gestionnaire de stock'),('CAISSIER','Caissier'),('GESTION','Responsable de gestion')]
    role=models.CharField(max_length=20,choices=ROLE_CHOICES,default='CAISSIER')
    telephone=models.CharField(max_length=30,blank=True)
    def __str__(self): return self.get_full_name() or self.username

class Categorie(models.Model):
    nom=models.CharField(max_length=100,unique=True)
    description=models.TextField(blank=True)
    def __str__(self): return self.nom

class Fournisseur(models.Model):
    nom=models.CharField(max_length=180)
    adresse=models.TextField(blank=True); telephone=models.CharField(max_length=40,blank=True)
    email=models.EmailField(blank=True); identifiant_fiscal=models.CharField(max_length=100,blank=True)
    contact_principal=models.CharField(max_length=150,blank=True); actif=models.BooleanField(default=True)
    cree_le=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.nom

class Client(models.Model):
    nom=models.CharField(max_length=160,blank=True); telephone=models.CharField(max_length=40,blank=True)
    email=models.EmailField(blank=True); adresse=models.TextField(blank=True); actif=models.BooleanField(default=True)
    def __str__(self): return self.nom or 'Client comptoir'

class Medicament(models.Model):
    nom=models.CharField(max_length=180)
    denomination_generique=models.CharField(max_length=180,blank=True)
    categorie=models.ForeignKey(Categorie,on_delete=models.PROTECT,related_name='medicaments')
    forme=models.CharField(max_length=100,blank=True); dosage=models.CharField(max_length=100,blank=True)
    laboratoire=models.CharField(max_length=150,blank=True)
    code_barres=models.CharField(max_length=100,blank=True,null=True,unique=True)
    photo=models.ImageField(upload_to='medicaments/',blank=True,null=True)
    prix_achat=models.DecimalField(max_digits=12,decimal_places=2,validators=[MinValueValidator(Decimal('0'))])
    prix_vente=models.DecimalField(max_digits=12,decimal_places=2,validators=[MinValueValidator(Decimal('0'))])
    seuil_alerte=models.PositiveIntegerField(default=5); actif=models.BooleanField(default=True)
    cree_le=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['nom']
    def __str__(self): return f'{self.nom} {self.dosage}'.strip()
    @property
    def stock_disponible(self):
        return sum(l.quantite for l in self.lots.filter(bloque=False,date_peremption__gte=timezone.localdate()))

class LotStock(models.Model):
    medicament=models.ForeignKey(Medicament,on_delete=models.PROTECT,related_name='lots')
    numero_lot=models.CharField(max_length=100)
    date_peremption=models.DateField()
    quantite=models.PositiveIntegerField(default=0)
    bloque=models.BooleanField(default=False)
    cree_le=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['date_peremption']; constraints=[models.UniqueConstraint(fields=['medicament','numero_lot'],name='lot_unique_par_medicament')]
    def __str__(self): return f'{self.medicament.nom} - {self.numero_lot}'
    @property
    def perime(self): return self.date_peremption < timezone.localdate()

class CommandeAchat(models.Model):
    STATUT=[('BROUILLON','Brouillon'),('COMMANDEE','Commandée'),('PARTIELLE','Partiellement réceptionnée'),('RECUE','Entièrement réceptionnée'),('ANNULEE','Annulée')]
    numero=models.CharField(max_length=30,unique=True); fournisseur=models.ForeignKey(Fournisseur,on_delete=models.PROTECT)
    statut=models.CharField(max_length=20,choices=STATUT,default='BROUILLON')
    cree_par=models.ForeignKey(Utilisateur,on_delete=models.PROTECT,related_name='achats_crees')
    cree_le=models.DateTimeField(auto_now_add=True); valide_le=models.DateTimeField(null=True,blank=True)
    @property
    def total(self): return sum((l.quantite*l.prix_unitaire for l in self.lignes.all()),Decimal('0'))
    def __str__(self): return self.numero

class LigneAchat(models.Model):
    commande=models.ForeignKey(CommandeAchat,on_delete=models.CASCADE,related_name='lignes')
    medicament=models.ForeignKey(Medicament,on_delete=models.PROTECT)
    quantite=models.PositiveIntegerField(validators=[MinValueValidator(1)])
    prix_unitaire=models.DecimalField(max_digits=12,decimal_places=2,validators=[MinValueValidator(Decimal('0'))])
    recue=models.PositiveIntegerField(default=0)

class ReceptionAchat(models.Model):
    commande=models.ForeignKey(CommandeAchat,on_delete=models.PROTECT,related_name='receptions')
    numero=models.CharField(max_length=30,unique=True); recue_par=models.ForeignKey(Utilisateur,on_delete=models.PROTECT)
    recue_le=models.DateTimeField(auto_now_add=True); commentaire=models.TextField(blank=True)

class LigneReception(models.Model):
    reception=models.ForeignKey(ReceptionAchat,on_delete=models.CASCADE,related_name='lignes')
    ligne_achat=models.ForeignKey(LigneAchat,on_delete=models.PROTECT)
    numero_lot=models.CharField(max_length=100); date_peremption=models.DateField(); quantite=models.PositiveIntegerField(validators=[MinValueValidator(1)])

class MouvementStock(models.Model):
    TYPES=[('ENTREE','Entrée'),('VENTE','Vente'),('RETOUR','Retour'),('AJUSTEMENT','Ajustement'),('PERTE','Perte')]
    medicament=models.ForeignKey(Medicament,on_delete=models.PROTECT); lot=models.ForeignKey(LotStock,on_delete=models.PROTECT,null=True,blank=True)
    type_mouvement=models.CharField(max_length=20,choices=TYPES); quantite=models.IntegerField()
    reference=models.CharField(max_length=100,blank=True); motif=models.TextField(blank=True)
    utilisateur=models.ForeignKey(Utilisateur,on_delete=models.PROTECT); date_mouvement=models.DateTimeField(auto_now_add=True)

class Vente(models.Model):
    STATUT=[('VALIDEE','Validée'),('ANNULEE','Annulée')]
    numero=models.CharField(max_length=30,unique=True); client=models.ForeignKey(Client,on_delete=models.PROTECT,null=True,blank=True)
    caissier=models.ForeignKey(Utilisateur,on_delete=models.PROTECT); statut=models.CharField(max_length=15,choices=STATUT,default='VALIDEE')
    total=models.DecimalField(max_digits=14,decimal_places=2,default=0); cree_le=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.numero

class LigneVente(models.Model):
    vente=models.ForeignKey(Vente,on_delete=models.CASCADE,related_name='lignes')
    medicament=models.ForeignKey(Medicament,on_delete=models.PROTECT); lot=models.ForeignKey(LotStock,on_delete=models.PROTECT)
    quantite=models.PositiveIntegerField(); prix_unitaire=models.DecimalField(max_digits=12,decimal_places=2)
    @property
    def sous_total(self): return self.quantite*self.prix_unitaire

class Paiement(models.Model):
    MODES=[('ESPECES','Espèces'),('MOBILE_MONEY','Mobile money'),('CARTE','Carte'),('AUTRE','Autre')]
    STATUT=[('CONFIRME','Confirmé'),('EN_ATTENTE','En attente'),('REFUSE','Refusé')]
    vente=models.ForeignKey(Vente,on_delete=models.PROTECT,related_name='paiements')
    mode=models.CharField(max_length=20,choices=MODES); montant=models.DecimalField(max_digits=14,decimal_places=2)
    statut=models.CharField(max_length=15,choices=STATUT,default='CONFIRME'); reference_externe=models.CharField(max_length=120,blank=True)
    cree_le=models.DateTimeField(auto_now_add=True)

class RetourVente(models.Model):
    vente=models.ForeignKey(Vente,on_delete=models.PROTECT,related_name='retours')
    ligne_vente=models.ForeignKey(LigneVente,on_delete=models.PROTECT)
    quantite=models.PositiveIntegerField(); motif=models.TextField()
    remise_en_stock=models.BooleanField(default=False); remboursement=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    traite_par=models.ForeignKey(Utilisateur,on_delete=models.PROTECT); cree_le=models.DateTimeField(auto_now_add=True)

class JournalAudit(models.Model):
    utilisateur=models.ForeignKey(Utilisateur,on_delete=models.PROTECT,null=True)
    action=models.CharField(max_length=100); objet=models.CharField(max_length=150,blank=True)
    details=models.TextField(blank=True); adresse_ip=models.GenericIPAddressField(null=True,blank=True)
    date_action=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-date_action']

class JournalRequete(models.Model):
    utilisateur=models.ForeignKey(Utilisateur,on_delete=models.SET_NULL,null=True,blank=True)
    methode=models.CharField(max_length=10)
    chemin=models.CharField(max_length=500)
    statut=models.PositiveSmallIntegerField()
    duree_ms=models.PositiveIntegerField()
    date_requete=models.DateTimeField(auto_now_add=True,db_index=True)

    class Meta:
        ordering=['-date_requete']
        verbose_name='journal de requête'
        verbose_name_plural='journaux de requêtes'

    def __str__(self):
        return f'{self.methode} {self.chemin} — {self.statut}'
