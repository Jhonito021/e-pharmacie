import json
from datetime import timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Sum, F, Count
from django.http import HttpResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .models import *
from .forms import *
from .services import *
from .decorators import roles

@login_required
def dashboard(request):
 today=timezone.localdate(); start=request.GET.get('debut'); end=request.GET.get('fin')
 ventes=Vente.objects.filter(statut='VALIDEE')
 if start: ventes=ventes.filter(cree_le__date__gte=start)
 if end: ventes=ventes.filter(cree_le__date__lte=end)
 if not start and not end: ventes=ventes.filter(cree_le__date=today)
 low=[m for m in Medicament.objects.filter(actif=True) if m.stock_disponible <= m.seuil_alerte]
 expiring=LotStock.objects.filter(date_peremption__gte=today,date_peremption__lte=today+timedelta(days=90),quantite__gt=0,bloque=False).select_related('medicament').order_by('date_peremption')
 expired=LotStock.objects.filter(date_peremption__lt=today,quantite__gt=0).select_related('medicament')
 context={'medicaments':Medicament.objects.filter(actif=True).count(),'ventes_total':ventes.aggregate(s=Sum('total'))['s'] or 0,'ventes_count':ventes.count(),'stocks_faibles':low,'peremptions':expiring,'lots_perimes':expired,'top':LigneVente.objects.values('medicament__nom').annotate(q=Sum('quantite')).order_by('-q')[:5],'debut':start or today,'fin':end or today}
 return render(request,'pharmacie/dashboard.html',context)

@login_required
def liste_medicaments(request):
 qs=Medicament.objects.select_related('categorie').all()
 q=request.GET.get('q',''); cat=request.GET.get('categorie','')
 if q: qs=qs.filter(nom__icontains=q) | qs.filter(code_barres__icontains=q)
 if cat: qs=qs.filter(categorie_id=cat)
 page=Paginator(qs.order_by('nom'),10).get_page(request.GET.get('page'))
 return render(request,'pharmacie/medicaments.html',{'page':page,'categories':Categorie.objects.all(),'q':q,'cat':cat})
@login_required
def medicament_form(request,pk=None):
 obj=get_object_or_404(Medicament,pk=pk) if pk else None
 form=MedicamentForm(request.POST or None,request.FILES or None,instance=obj)
 if form.is_valid(): form.save(); audit(request.user,'MEDICAMENT_ENREGISTRE',str(form.instance),request=request); messages.success(request,'Médicament enregistré.'); return redirect('medicaments')
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Modifier le médicament' if obj else 'Nouveau médicament'})
@login_required
@roles('ADMIN','PHARMACIEN')
@require_POST
def archiver_medicament(request,pk):
 m=get_object_or_404(Medicament,pk=pk); m.actif=False; m.save(update_fields=['actif']); audit(request.user,'MEDICAMENT_ARCHIVE',str(m),request=request); messages.success(request,'Médicament archivé.'); return redirect('medicaments')

@login_required
def categories(request):
 form=CategorieForm(request.POST or None)
 if form.is_valid(): form.save(); messages.success(request,'Catégorie ajoutée.'); return redirect('categories')
 return render(request,'pharmacie/categories.html',{'categories':Categorie.objects.all(),'form':form})
@login_required
@roles('ADMIN','PHARMACIEN')
@require_POST
def supprimer_categorie(request,pk):
 c=get_object_or_404(Categorie,pk=pk)
 if c.medicaments.exists(): messages.error(request,'Cette catégorie est utilisée et ne peut pas être supprimée.')
 else: c.delete(); messages.success(request,'Catégorie supprimée.')
 return redirect('categories')

@login_required
def fournisseurs(request):
 q=request.GET.get('q',''); qs=Fournisseur.objects.all()
 if q: qs=qs.filter(nom__icontains=q) | qs.filter(telephone__icontains=q)
 return render(request,'pharmacie/fournisseurs.html',{'fournisseurs':qs,'q':q})
@login_required
def fournisseur_form(request,pk=None):
 obj=get_object_or_404(Fournisseur,pk=pk) if pk else None; form=FournisseurForm(request.POST or None,instance=obj)
 if form.is_valid(): form.save(); messages.success(request,'Fournisseur enregistré.'); return redirect('fournisseurs')
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Fournisseur'})
@login_required
def clients(request): return render(request,'pharmacie/clients.html',{'clients':Client.objects.all()})
@login_required
def client_form(request,pk=None):
 obj=get_object_or_404(Client,pk=pk) if pk else None; form=ClientForm(request.POST or None,instance=obj)
 if form.is_valid(): form.save(); messages.success(request,'Client enregistré.'); return redirect('clients')
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Client'})

@login_required
@roles('ADMIN','PHARMACIEN','STOCK')
def achats(request): return render(request,'pharmacie/achats.html',{'achats':CommandeAchat.objects.select_related('fournisseur').order_by('-cree_le')})
@login_required
@roles('ADMIN','PHARMACIEN','STOCK')
def achat_creer(request):
 form=CommandeAchatForm(request.POST or None)
 if form.is_valid():
  obj=form.save(commit=False); obj.numero=f'A-{timezone.now():%Y%m%d%H%M%S%f}'; obj.cree_par=request.user; obj.save(); return redirect('achat_detail',pk=obj.pk)
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Nouvelle commande d’achat'})
@login_required
@roles('ADMIN','PHARMACIEN','STOCK')
def achat_detail(request,pk):
 obj=get_object_or_404(CommandeAchat,pk=pk); form=LigneAchatForm(request.POST or None)
 if request.method=='POST' and 'ajouter_ligne' in request.POST and form.is_valid() and obj.statut=='BROUILLON':
  line=form.save(commit=False); line.commande=obj; line.save(); messages.success(request,'Ligne ajoutée.'); return redirect('achat_detail',pk=pk)
 if request.method=='POST' and 'commander' in request.POST and obj.lignes.exists(): obj.statut='COMMANDEE'; obj.valide_le=timezone.now(); obj.save(); return redirect('achat_detail',pk=pk)
 if request.method=='POST' and 'recevoir' in request.POST:
  try:
   line=get_object_or_404(LigneAchat,pk=request.POST.get('ligne'),commande=obj)
   reception,_=ReceptionAchat.objects.get_or_create(commande=obj,defaults={'numero':f'R-{timezone.now():%Y%m%d%H%M%S%f}','recue_par':request.user})
   receptionner_ligne(line,int(request.POST.get('quantite')),request.POST.get('numero_lot'),timezone.datetime.fromisoformat(request.POST.get('date_peremption')).date(),reception,request.user)
   messages.success(request,'Réception enregistrée et stock mis à jour.')
  except (ValidationError,ValueError,TypeError) as e: messages.error(request,str(e))
  return redirect('achat_detail',pk=pk)
 return render(request,'pharmacie/achat_detail.html',{'achat':obj,'form':form})

@login_required
def stock(request):
 lots=LotStock.objects.select_related('medicament').order_by('date_peremption')
 return render(request,'pharmacie/stock.html',{'lots':lots,'mouvements':MouvementStock.objects.select_related('medicament','utilisateur').order_by('-date_mouvement')[:30]})
@login_required
@roles('ADMIN','PHARMACIEN','STOCK')
def inventaire(request):
 if request.method=='POST':
  lot=get_object_or_404(LotStock,pk=request.POST.get('lot'))
  try: ajuster_stock(lot,int(request.POST.get('quantite')),request.user,request.POST.get('motif','Inventaire physique')); messages.success(request,'Inventaire enregistré.')
  except (ValueError,ValidationError) as e: messages.error(request,str(e))
  return redirect('stock')
 return redirect('stock')

@login_required
@roles('ADMIN','PHARMACIEN','CAISSIER')
def caisse(request):
 meds=Medicament.objects.filter(actif=True).order_by('nom')
 if request.method=='POST':
  try:
   raw=json.loads(request.POST.get('panier','[]')); client_id=request.POST.get('client') or None
   client=Client.objects.filter(pk=client_id).first() if client_id else None
   vente=effectuer_vente(request.user,raw,request.POST.get('mode_paiement','ESPECES'),client,request.POST.get('reference',''))
   messages.success(request,f'Vente {vente.numero} enregistrée.'); return redirect('recu_pdf',pk=vente.pk)
  except Exception as e: messages.error(request,str(e))
 return render(request,'pharmacie/caisse.html',{'medicaments':meds,'clients':Client.objects.filter(actif=True)})
@login_required
def ventes(request): return render(request,'pharmacie/ventes.html',{'ventes':Vente.objects.select_related('caissier','client').order_by('-cree_le')[:200]})
@login_required
def retour(request,pk):
 vente=get_object_or_404(Vente,pk=pk)
 if request.method=='POST':
  try:
   ligne=get_object_or_404(LigneVente,pk=request.POST.get('ligne'),vente=vente); q=int(request.POST.get('quantite'))
   deja=vente.retours.filter(ligne_vente=ligne).aggregate(s=Sum('quantite'))['s'] or 0
   if q<=0 or q+deja>ligne.quantite: raise ValidationError('Quantité de retour invalide.')
   eligible=request.POST.get('remise_en_stock')=='on' and not ligne.lot.perime and not ligne.lot.bloque
   RetourVente.objects.create(vente=vente,ligne_vente=ligne,quantite=q,motif=request.POST.get('motif',''),remise_en_stock=eligible,remboursement=ligne.prix_unitaire*q,traite_par=request.user)
   if eligible:
    ligne.lot.quantite=F('quantite')+q; ligne.lot.save(); MouvementStock.objects.create(medicament=ligne.medicament,lot=ligne.lot,type_mouvement='RETOUR',quantite=q,reference=vente.numero,utilisateur=request.user)
   audit(request.user,'RETOUR_VENTE',vente.numero,f'{q} x {ligne.medicament}')
   messages.success(request,'Retour enregistré.')
  except (ValueError,ValidationError) as e: messages.error(request,str(e))
  return redirect('ventes')
 return render(request,'pharmacie/retour.html',{'vente':vente})

@login_required
def recu_pdf(request,pk):
 vente=get_object_or_404(Vente,pk=pk); response=HttpResponse(content_type='application/pdf'); response['Content-Disposition']=f'inline; filename="recu-{vente.numero}.pdf"'
 p=canvas.Canvas(response,pagesize=A4); y=800
 p.setFont('Helvetica-Bold',18); p.drawString(50,y,'PHARMAGEST - Reçu de vente'); y-=35
 p.setFont('Helvetica',10); p.drawString(50,y,f'Numéro : {vente.numero}'); y-=18; p.drawString(50,y,f'Date : {vente.cree_le:%d/%m/%Y %H:%M}'); y-=18; p.drawString(50,y,f'Caissier : {vente.caissier}'); y-=30
 p.setFont('Helvetica-Bold',10); p.drawString(50,y,'Médicament'); p.drawString(300,y,'Qté'); p.drawString(360,y,'Prix'); p.drawString(450,y,'Total'); y-=18
 p.setFont('Helvetica',10)
 for l in vente.lignes.all():
  p.drawString(50,y,l.medicament.nom[:38]); p.drawString(300,y,str(l.quantite)); p.drawString(360,y,str(l.prix_unitaire)); p.drawString(450,y,str(l.sous_total)); y-=18
 p.setFont('Helvetica-Bold',12); p.drawString(350,y-15,f'TOTAL : {vente.total}'); p.showPage(); p.save(); return response

@login_required
@roles('ADMIN','PHARMACIEN','STOCK')
def achat_pdf(request,pk):
 obj=get_object_or_404(CommandeAchat,pk=pk)
 response=HttpResponse(content_type='application/pdf'); response['Content-Disposition']=f'inline; filename="commande-{obj.numero}.pdf"'
 p=canvas.Canvas(response,pagesize=A4); y=800
 p.setFont('Helvetica-Bold',17); p.drawString(45,y,'PHARMAGEST - Bon de commande'); y-=32
 p.setFont('Helvetica',10); p.drawString(45,y,f'Commande : {obj.numero}'); y-=17; p.drawString(45,y,f'Fournisseur : {obj.fournisseur.nom}'); y-=17; p.drawString(45,y,f'Date : {obj.cree_le:%d/%m/%Y}'); y-=28
 p.setFont('Helvetica-Bold',10); p.drawString(45,y,'Médicament'); p.drawString(310,y,'Qté'); p.drawString(365,y,'Prix unitaire'); p.drawString(465,y,'Total'); y-=18; p.setFont('Helvetica',9)
 for line in obj.lignes.select_related('medicament'):
  p.drawString(45,y,line.medicament.nom[:42]); p.drawString(310,y,str(line.quantite)); p.drawString(365,y,str(line.prix_unitaire)); p.drawString(465,y,str(line.quantite*line.prix_unitaire)); y-=17
 p.setFont('Helvetica-Bold',12); p.drawString(350,y-18,f'TOTAL : {obj.total} Ar'); p.showPage(); p.save(); return response

@login_required
@roles('ADMIN','PHARMACIEN','GESTION','STOCK')
def rapport_pdf(request,kind):
 response=HttpResponse(content_type='application/pdf'); response['Content-Disposition']=f'inline; filename="rapport-{kind}.pdf"'
 p=canvas.Canvas(response,pagesize=A4); y=800; today=timezone.localdate()
 titles={'stock':'Rapport de stock','ventes':'Rapport des ventes','achats':'Rapport des achats','peremption':'Lots proches de péremption'}
 if kind not in titles: return HttpResponse('Rapport inconnu',status=404)
 p.setFont('Helvetica-Bold',17); p.drawString(45,y,'PHARMAGEST - '+titles[kind]); y-=28; p.setFont('Helvetica',9); p.drawString(45,y,f'Généré le {today:%d/%m/%Y}'); y-=25
 if kind=='stock':
  p.setFont('Helvetica-Bold',9); p.drawString(45,y,'Médicament'); p.drawString(290,y,'Lot'); p.drawString(390,y,'Péremption'); p.drawString(500,y,'Qté'); y-=17
  for lot in LotStock.objects.select_related('medicament').order_by('date_peremption'):
   if y<55: p.showPage(); y=800
   p.setFont('Helvetica',8); p.drawString(45,y,lot.medicament.nom[:38]); p.drawString(290,y,lot.numero_lot[:18]); p.drawString(390,y,lot.date_peremption.strftime('%d/%m/%Y')); p.drawString(500,y,str(lot.quantite)); y-=15
 elif kind=='ventes':
  qs=Vente.objects.filter(statut='VALIDEE').order_by('-cree_le'); p.setFont('Helvetica-Bold',9); p.drawString(45,y,'Référence'); p.drawString(230,y,'Date'); p.drawString(350,y,'Caissier'); p.drawString(490,y,'Total'); y-=17
  for v in qs:
   if y<55: p.showPage(); y=800
   p.setFont('Helvetica',8); p.drawString(45,y,v.numero); p.drawString(230,y,v.cree_le.strftime('%d/%m/%Y')); p.drawString(350,y,str(v.caissier)[:22]); p.drawString(490,y,str(v.total)); y-=15
 elif kind=='achats':
  qs=CommandeAchat.objects.select_related('fournisseur').order_by('-cree_le'); p.setFont('Helvetica-Bold',9); p.drawString(45,y,'Référence'); p.drawString(230,y,'Fournisseur'); p.drawString(410,y,'Statut'); p.drawString(500,y,'Total'); y-=17
  for a in qs:
   if y<55: p.showPage(); y=800
   p.setFont('Helvetica',8); p.drawString(45,y,a.numero); p.drawString(230,y,a.fournisseur.nom[:25]); p.drawString(410,y,a.get_statut_display()); p.drawString(500,y,str(a.total)); y-=15
 else:
  qs=LotStock.objects.filter(quantite__gt=0,date_peremption__gte=today,date_peremption__lte=today+timedelta(days=90)).select_related('medicament').order_by('date_peremption'); p.setFont('Helvetica-Bold',9); p.drawString(45,y,'Médicament'); p.drawString(300,y,'Lot'); p.drawString(410,y,'Péremption'); p.drawString(510,y,'Qté'); y-=17
  for lot in qs:
   if y<55: p.showPage(); y=800
   p.setFont('Helvetica',8); p.drawString(45,y,lot.medicament.nom[:40]); p.drawString(300,y,lot.numero_lot[:18]); p.drawString(410,y,lot.date_peremption.strftime('%d/%m/%Y')); p.drawString(510,y,str(lot.quantite)); y-=15
 p.showPage(); p.save(); return response

@login_required
@roles('ADMIN','PHARMACIEN','GESTION')
def rapports(request):
 debut=request.GET.get('debut'); fin=request.GET.get('fin'); qs=Vente.objects.filter(statut='VALIDEE')
 if debut: qs=qs.filter(cree_le__date__gte=debut)
 if fin: qs=qs.filter(cree_le__date__lte=fin)
 return render(request,'pharmacie/rapports.html',{'ventes':qs,'total':qs.aggregate(s=Sum('total'))['s'] or 0,'debut':debut,'fin':fin,'achats':CommandeAchat.objects.all()})
@login_required
@roles('ADMIN')
def utilisateurs(request): return render(request,'pharmacie/utilisateurs.html',{'utilisateurs':Utilisateur.objects.all()})
@login_required
@roles('ADMIN')
def utilisateur_creer(request):
 form=UtilisateurCreationForm(request.POST or None)
 if form.is_valid(): form.save(); messages.success(request,'Compte créé.'); return redirect('utilisateurs')
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Créer un utilisateur'})
@login_required
@roles('ADMIN')
def audit_logs(request): return render(request,'pharmacie/audit.html',{'logs':JournalAudit.objects.select_related('utilisateur')[:200]})
