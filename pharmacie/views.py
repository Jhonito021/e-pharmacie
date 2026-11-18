import json
from datetime import timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
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
 top=list(LigneVente.objects.filter(vente__in=ventes).values('medicament__nom').annotate(q=Sum('quantite')).order_by('-q')[:5])
 total_unites=LigneVente.objects.filter(vente__in=ventes).aggregate(s=Sum('quantite'))['s'] or 0
 autres_unites=total_unites-sum(item['q'] for item in top)
 chart_labels=[item['medicament__nom'] for item in top]
 chart_values=[item['q'] for item in top]
 if autres_unites:
  chart_labels.append('Autres')
  chart_values.append(autres_unites)
 low=[m for m in Medicament.objects.filter(actif=True) if m.stock_disponible <= m.seuil_alerte]
 expiring=LotStock.objects.filter(date_peremption__gte=today,date_peremption__lte=today+timedelta(days=90),quantite__gt=0,bloque=False).select_related('medicament').order_by('date_peremption')
 expired=LotStock.objects.filter(date_peremption__lt=today,quantite__gt=0).select_related('medicament')
 context={'medicaments':Medicament.objects.filter(actif=True).count(),'ventes_total':ventes.aggregate(s=Sum('total'))['s'] or 0,'ventes_count':ventes.count(),'stocks_faibles':low,'peremptions':expiring,'lots_perimes':expired,'top':top,'chart_labels':chart_labels,'chart_values':chart_values,'debut':start or today,'fin':end or today}
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
def medicament_detail(request,pk):
 medicament=get_object_or_404(Medicament.objects.select_related('categorie'),pk=pk)
 return render(request,'pharmacie/medicament_detail.html',{'medicament':medicament,'lots':medicament.lots.order_by('date_peremption')})

@login_required
def medicament_form(request,pk=None):
 obj=get_object_or_404(Medicament,pk=pk) if pk else None
 form=MedicamentForm(request.POST or None,request.FILES or None,instance=obj)
 if form.is_valid():
  medicament=form.save()
  audit(request.user,'MEDICAMENT_MODIFIE' if obj else 'MEDICAMENT_CREE',str(medicament),request=request)
  messages.success(request,'Médicament enregistré.')
  return redirect('medicament_detail',pk=medicament.pk)
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Modifier le médicament' if obj else 'Nouveau médicament'})

@login_required
@roles('ADMIN','PHARMACIEN')
@require_POST
def archiver_medicament(request,pk):
 m=get_object_or_404(Medicament,pk=pk); m.actif=False; m.save(update_fields=['actif']); audit(request.user,'MEDICAMENT_ARCHIVE',str(m),request=request); messages.success(request,'Médicament archivé.'); return redirect('medicaments')

@login_required
@roles('ADMIN','PHARMACIEN')
@require_POST
def reactiver_medicament(request,pk):
 m=get_object_or_404(Medicament,pk=pk); m.actif=True; m.save(update_fields=['actif']); audit(request.user,'MEDICAMENT_REACTIVE',str(m),request=request); messages.success(request,'Médicament réactivé.'); return redirect('medicament_detail',pk=m.pk)

@login_required
def categories(request):
 form=CategorieForm(request.POST or None)
 if form.is_valid():
  categorie=form.save()
  audit(request.user,'CATEGORIE_CREEE',str(categorie),request=request)
  messages.success(request,'Catégorie ajoutée.')
  return redirect('categories')
 return render(request,'pharmacie/categories.html',{'categories':Categorie.objects.all(),'form':form})

@login_required
def categorie_form(request,pk):
 categorie=get_object_or_404(Categorie,pk=pk)
 form=CategorieForm(request.POST or None,instance=categorie)
 if form.is_valid():
  form.save()
  audit(request.user,'CATEGORIE_MODIFIEE',str(categorie),request=request)
  messages.success(request,'Catégorie modifiée.')
  return redirect('categories')
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Modifier la catégorie'})

@login_required
@roles('ADMIN','PHARMACIEN')
@require_POST
def supprimer_categorie(request,pk):
 c=get_object_or_404(Categorie,pk=pk)
 if c.medicaments.exists(): messages.error(request,'Cette catégorie est utilisée et ne peut pas être supprimée.')
 else:
  audit(request.user,'CATEGORIE_SUPPRIMEE',str(c),request=request)
  c.delete()
  messages.success(request,'Catégorie supprimée.')
 return redirect('categories')

@login_required
def fournisseurs(request):
 q=request.GET.get('q',''); qs=Fournisseur.objects.all()
 if q: qs=qs.filter(nom__icontains=q) | qs.filter(telephone__icontains=q)
 return render(request,'pharmacie/fournisseurs.html',{'fournisseurs':qs,'q':q})

@login_required
def fournisseur_detail(request,pk):
 fournisseur=get_object_or_404(Fournisseur,pk=pk)
 commandes=CommandeAchat.objects.filter(fournisseur=fournisseur).order_by('-cree_le')[:10]
 return render(request,'pharmacie/fournisseur_detail.html',{'fournisseur':fournisseur,'commandes':commandes})

@login_required
def fournisseur_form(request,pk=None):
 obj=get_object_or_404(Fournisseur,pk=pk) if pk else None; form=FournisseurForm(request.POST or None,instance=obj)
 if form.is_valid():
  fournisseur=form.save()
  audit(request.user,'FOURNISSEUR_MODIFIE' if obj else 'FOURNISSEUR_CREE',str(fournisseur),request=request)
  messages.success(request,'Fournisseur enregistré.')
  return redirect('fournisseurs')
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Modifier le fournisseur' if obj else 'Nouveau fournisseur'})

@login_required
@require_POST
def changer_statut_fournisseur(request,pk):
 fournisseur=get_object_or_404(Fournisseur,pk=pk)
 fournisseur.actif=not fournisseur.actif
 fournisseur.save(update_fields=['actif'])
 action='FOURNISSEUR_REACTIVE' if fournisseur.actif else 'FOURNISSEUR_ARCHIVE'
 audit(request.user,action,str(fournisseur),request=request)
 messages.success(request,'Fournisseur réactivé.' if fournisseur.actif else 'Fournisseur désactivé.')
 return redirect('fournisseurs')

@login_required
def clients(request):
 q=request.GET.get('q','')
 qs=Client.objects.all()
 if q: qs=qs.filter(nom__icontains=q) | qs.filter(telephone__icontains=q) | qs.filter(email__icontains=q)
 return render(request,'pharmacie/clients.html',{'clients':qs,'q':q})

@login_required
def client_detail(request,pk):
 client=get_object_or_404(Client,pk=pk)
 ventes=Vente.objects.filter(client=client).order_by('-cree_le')[:10]
 return render(request,'pharmacie/client_detail.html',{'client':client,'ventes':ventes})

@login_required
def client_form(request,pk=None):
 obj=get_object_or_404(Client,pk=pk) if pk else None; form=ClientForm(request.POST or None,instance=obj)
 if form.is_valid():
  client=form.save()
  audit(request.user,'CLIENT_MODIFIE' if obj else 'CLIENT_CREE',str(client),request=request)
  messages.success(request,'Client enregistré.')
  return redirect('clients')
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Modifier le client' if obj else 'Nouveau client'})

@login_required
@require_POST
def changer_statut_client(request,pk):
 client=get_object_or_404(Client,pk=pk)
 client.actif=not client.actif
 client.save(update_fields=['actif'])
 action='CLIENT_REACTIVE' if client.actif else 'CLIENT_ARCHIVE'
 audit(request.user,action,str(client),request=request)
 messages.success(request,'Client réactivé.' if client.actif else 'Client désactivé.')
 return redirect('clients')

@login_required
@roles('ADMIN','PHARMACIEN','STOCK')
def achats(request): return render(request,'pharmacie/achats.html',{'achats':CommandeAchat.objects.select_related('fournisseur').order_by('-cree_le')})
@login_required
@roles('ADMIN','PHARMACIEN','STOCK')
def achat_creer(request):
 form=CommandeAchatForm(request.POST or None)
 if form.is_valid():
  obj=form.save(commit=False); obj.numero=f'A-{timezone.now():%Y%m%d%H%M%S%f}'; obj.cree_par=request.user; obj.save(); audit(request.user,'ACHAT_CREE',obj.numero,request=request); messages.success(request,'Brouillon de commande créé.'); return redirect('achat_detail',pk=obj.pk)
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Nouvelle commande d’achat'})

@login_required
@roles('ADMIN','PHARMACIEN','STOCK')
def achat_detail(request,pk):
 obj=get_object_or_404(CommandeAchat,pk=pk); form=LigneAchatForm(request.POST or None)
 if request.method=='POST' and 'ajouter_ligne' in request.POST and form.is_valid() and obj.statut=='BROUILLON':
  line=form.save(commit=False); line.commande=obj; line.save(); audit(request.user,'LIGNE_ACHAT_AJOUTEE',f'{obj.numero} · {line.medicament}',request=request); messages.success(request,'Ligne ajoutée.'); return redirect('achat_detail',pk=pk)
 if request.method=='POST' and 'commander' in request.POST and obj.statut=='BROUILLON' and obj.lignes.exists():
  obj.statut='COMMANDEE'; obj.valide_le=timezone.now(); obj.save(); audit(request.user,'ACHAT_COMMANDE',obj.numero,request=request); messages.success(request,'Commande validée.'); return redirect('achat_detail',pk=pk)
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
@roles('ADMIN','PHARMACIEN','STOCK')
@require_POST
def annuler_achat(request,pk):
 commande=get_object_or_404(CommandeAchat,pk=pk)
 peut_annuler=commande.statut in ('BROUILLON','COMMANDEE') and not commande.lignes.filter(recue__gt=0).exists()
 if not peut_annuler:
  messages.error(request,'Cette commande ne peut plus être annulée après sa réception ou son annulation.')
 else:
  commande.statut='ANNULEE'
  commande.save(update_fields=['statut'])
  audit(request.user,'ACHAT_ANNULE',commande.numero,request=request)
  messages.success(request,'Commande annulée.')
 return redirect('achat_detail',pk=commande.pk)

@login_required
@roles('ADMIN','PHARMACIEN','STOCK')
def ligne_achat_modifier(request,pk):
 ligne=get_object_or_404(LigneAchat.objects.select_related('commande'),pk=pk)
 if ligne.commande.statut!='BROUILLON':
  messages.error(request,'Les lignes ne peuvent être modifiées que sur un brouillon.')
  return redirect('achat_detail',pk=ligne.commande_id)
 form=LigneAchatForm(request.POST or None,instance=ligne)
 if form.is_valid():
  form.save()
  audit(request.user,'LIGNE_ACHAT_MODIFIEE',f'{ligne.commande.numero} · {ligne.medicament}',request=request)
  messages.success(request,'Ligne modifiée.')
  return redirect('achat_detail',pk=ligne.commande_id)
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Modifier une ligne de commande'})

@login_required
@roles('ADMIN','PHARMACIEN','STOCK')
@require_POST
def ligne_achat_supprimer(request,pk):
 ligne=get_object_or_404(LigneAchat.objects.select_related('commande','medicament'),pk=pk)
 commande=ligne.commande
 if commande.statut!='BROUILLON':
  messages.error(request,'Les lignes ne peuvent être supprimées que sur un brouillon.')
 else:
  audit(request.user,'LIGNE_ACHAT_SUPPRIMEE',f'{commande.numero} · {ligne.medicament}',request=request)
  ligne.delete()
  messages.success(request,'Ligne supprimée.')
 return redirect('achat_detail',pk=commande.pk)

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
def vente_detail(request,pk):
 vente=get_object_or_404(
  Vente.objects.select_related('client','caissier').prefetch_related(
   'lignes__medicament','lignes__lot','paiements','retours__ligne_vente__medicament'
  ),
  pk=pk,
 )
 return render(request,'pharmacie/vente_detail.html',{'vente':vente})

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
 achats=CommandeAchat.objects.exclude(statut='ANNULEE')
 if debut: qs=qs.filter(cree_le__date__gte=debut)
 if fin: qs=qs.filter(cree_le__date__lte=fin)
 if debut: achats=achats.filter(cree_le__date__gte=debut)
 if fin: achats=achats.filter(cree_le__date__lte=fin)
 ventes_par_categorie=[
  {'label':row['medicament__categorie__nom'],'value':row['total']}
  for row in LigneVente.objects.filter(vente__in=qs).values('medicament__categorie__nom')
  .annotate(total=Sum(F('quantite')*F('prix_unitaire'))).order_by('-total')
 ]
 achats_par_fournisseur=[
  {'label':row['commande__fournisseur__nom'],'value':row['total']}
  for row in LigneAchat.objects.filter(commande__in=achats,recue__gt=0)
  .values('commande__fournisseur__nom')
  .annotate(total=Sum(F('recue')*F('prix_unitaire'))).order_by('-total')
 ]
 paiements_par_mode=[
  {'label':dict(Paiement.MODES)[row['mode']],'value':row['total']}
  for row in Paiement.objects.filter(vente__in=qs,statut='CONFIRME')
  .values('mode').annotate(total=Sum('montant')).order_by('-total')
 ]
 stock_par_categorie=[
  {'label':row['medicament__categorie__nom'],'value':row['quantite']}
  for row in LotStock.objects.filter(
   medicament__actif=True,bloque=False,date_peremption__gte=timezone.localdate(),quantite__gt=0
  ).values('medicament__categorie__nom').annotate(quantite=Sum('quantite')).order_by('-quantite')
 ]
 charts=[
  {'id':'sales-category-chart','data_id':'sales-category-data','title':'Ventes par catégorie','unit':'Ar de chiffre d’affaires','data':ventes_par_categorie},
  {'id':'purchase-supplier-chart','data_id':'purchase-supplier-data','title':'Achats réceptionnés par fournisseur','unit':'Ar réceptionnés','data':achats_par_fournisseur},
  {'id':'payment-mode-chart','data_id':'payment-mode-data','title':'Paiements confirmés par mode','unit':'Ar encaissés','data':paiements_par_mode},
  {'id':'stock-category-chart','data_id':'stock-category-data','title':'Stock disponible par catégorie','unit':'unités disponibles','data':stock_par_categorie},
 ]
 total_receptionne=LigneAchat.objects.filter(
  commande__in=achats,recue__gt=0
 ).aggregate(total=Sum(F('recue')*F('prix_unitaire')))['total'] or 0
 context={
  'ventes':qs,'total':qs.aggregate(s=Sum('total'))['s'] or 0,
  'debut':debut,'fin':fin,'achats':achats,'total_receptionne':total_receptionne,
  'charts':charts,'has_charts':any(chart['data'] for chart in charts),
 }
 return render(request,'pharmacie/rapports.html',context)
@login_required
@roles('ADMIN')
def utilisateurs(request): return render(request,'pharmacie/utilisateurs.html',{'utilisateurs':Utilisateur.objects.all()})
@login_required
@roles('ADMIN')
def utilisateur_creer(request):
 form=UtilisateurCreationForm(request.POST or None)
 if form.is_valid():
  user=form.save()
  audit(request.user,'UTILISATEUR_CREE',user.username,request=request)
  messages.success(request,'Compte créé.')
  return redirect('utilisateurs')
 return render(request,'pharmacie/form.html',{'form':form,'titre':'Créer un utilisateur'})

@login_required
@roles('ADMIN')
def utilisateur_modifier(request,pk):
 user=get_object_or_404(Utilisateur,pk=pk)
 if user.is_superuser and not request.user.is_superuser:
  raise PermissionDenied
 form=UtilisateurUpdateForm(request.POST or None,instance=user)
 if form.is_valid():
  if user.pk==request.user.pk and not form.cleaned_data['is_active']:
   form.add_error('is_active','Vous ne pouvez pas désactiver votre propre compte.')
   return render(request,'pharmacie/form.html',{'form':form,'titre':f'Modifier {user.username}'})
  updated_user=form.save()
  audit(request.user,'UTILISATEUR_MODIFIE',updated_user.username,request=request)
  messages.success(request,'Compte modifié.')
  return redirect('utilisateurs')
 return render(request,'pharmacie/form.html',{'form':form,'titre':f'Modifier {user.username}'})

@login_required
@roles('ADMIN')
@require_POST
def changer_statut_utilisateur(request,pk):
 user=get_object_or_404(Utilisateur,pk=pk)
 if user.pk==request.user.pk:
  messages.error(request,'Vous ne pouvez pas désactiver votre propre compte depuis cette page.')
 elif user.is_superuser and not request.user.is_superuser:
  messages.error(request,'Seul un superutilisateur peut modifier le statut de ce compte.')
 else:
  user.is_active=not user.is_active
  user.save(update_fields=['is_active'])
  audit(request.user,'UTILISATEUR_REACTIVE' if user.is_active else 'UTILISATEUR_DESACTIVE',user.username,request=request)
  messages.success(request,'Compte réactivé.' if user.is_active else 'Compte désactivé.')
 return redirect('utilisateurs')
@login_required
@roles('ADMIN')
def audit_logs(request): return render(request,'pharmacie/audit.html',{'logs':JournalAudit.objects.select_related('utilisateur')[:200]})
