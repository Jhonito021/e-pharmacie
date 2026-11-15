from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import *

def audit(user, action, objet='', details='', request=None):
    ip=request.META.get('REMOTE_ADDR') if request else None
    JournalAudit.objects.create(utilisateur=user if getattr(user,'is_authenticated',False) else None, action=action, objet=objet, details=details, adresse_ip=ip)

@transaction.atomic
def receptionner_ligne(ligne, quantite, numero_lot, date_peremption, reception, user):
    if quantite <= 0 or ligne.recue + quantite > ligne.quantite: raise ValidationError('Quantité de réception invalide.')
    if date_peremption < timezone.localdate(): raise ValidationError('Impossible de réceptionner un lot déjà périmé.')
    lot, _ = LotStock.objects.select_for_update().get_or_create(medicament=ligne.medicament, numero_lot=numero_lot, defaults={'date_peremption':date_peremption})
    if lot.date_peremption != date_peremption: raise ValidationError('La date de péremption du lot ne correspond pas.')
    lot.quantite=F('quantite')+quantite; lot.save(); lot.refresh_from_db()
    ligne.recue=F('recue')+quantite; ligne.save(); ligne.refresh_from_db()
    MouvementStock.objects.create(medicament=ligne.medicament,lot=lot,type_mouvement='ENTREE',quantite=quantite,reference=reception.numero,utilisateur=user)
    reception.lignes.create(ligne_achat=ligne,numero_lot=numero_lot,date_peremption=date_peremption,quantite=quantite)
    commande=ligne.commande
    if all(x.recue >= x.quantite for x in commande.lignes.all()): commande.statut='RECUE'
    else: commande.statut='PARTIELLE'
    commande.save(update_fields=['statut'])
    audit(user,'RECEPTION_ACHAT',commande.numero,f'{quantite} unités de {ligne.medicament}')

@transaction.atomic
def effectuer_vente(user, lignes, mode_paiement='ESPECES', client=None, reference=''):
    if not lignes: raise ValidationError('Le panier est vide.')
    vente=Vente.objects.create(numero=f'V-{timezone.now():%Y%m%d%H%M%S%f}',caissier=user,client=client,total=0)
    total=Decimal('0')
    for item in lignes:
        med=Medicament.objects.get(pk=item['medicament_id'],actif=True)
        qte=int(item['quantite'])
        if qte <= 0: raise ValidationError('La quantité doit être positive.')
        lots=list(LotStock.objects.select_for_update().filter(medicament=med,bloque=False,date_peremption__gte=timezone.localdate(),quantite__gt=0).order_by('date_peremption'))
        disponible=sum(l.quantite for l in lots)
        if qte > disponible: raise ValidationError(f'Stock insuffisant pour {med.nom}. Disponible : {disponible}.')
        restant=qte
        for lot in lots:
            pris=min(restant,lot.quantite)
            if not pris: continue
            lot.quantite=F('quantite')-pris; lot.save(); lot.refresh_from_db()
            LigneVente.objects.create(vente=vente,medicament=med,lot=lot,quantite=pris,prix_unitaire=med.prix_vente)
            MouvementStock.objects.create(medicament=med,lot=lot,type_mouvement='VENTE',quantite=-pris,reference=vente.numero,utilisateur=user)
            total += med.prix_vente*pris; restant-=pris
            if restant==0: break
    vente.total=total; vente.save(update_fields=['total'])
    Paiement.objects.create(vente=vente,mode=mode_paiement,montant=total,statut='CONFIRME' if mode_paiement!='MOBILE_MONEY' or reference else 'EN_ATTENTE',reference_externe=reference)
    audit(user,'VENTE_VALIDEE',vente.numero,f'Total {total}')
    return vente

@transaction.atomic
def ajuster_stock(lot, nouvelle_quantite, user, motif):
    if nouvelle_quantite < 0: raise ValidationError('Le stock ne peut pas être négatif.')
    lot=LotStock.objects.select_for_update().get(pk=lot.pk)
    delta=nouvelle_quantite-lot.quantite
    if delta:
        lot.quantite=nouvelle_quantite; lot.save(update_fields=['quantite'])
        MouvementStock.objects.create(medicament=lot.medicament,lot=lot,type_mouvement='AJUSTEMENT',quantite=delta,motif=motif,utilisateur=user)
        audit(user,'AJUSTEMENT_STOCK',str(lot),f'{delta:+d} : {motif}')
