from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Categorie,
    Client,
    CommandeAchat,
    Fournisseur,
    JournalAudit,
    JournalRequete,
    LigneAchat,
    LigneReception,
    LigneVente,
    LotStock,
    Medicament,
    MouvementStock,
    Paiement,
    ReceptionAchat,
    RetourVente,
    Utilisateur,
    Vente,
)


class ReadOnlyAdminMixin:
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReadOnlyInlineMixin:
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class LigneVenteInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = LigneVente
    readonly_fields = ('medicament', 'lot', 'quantite', 'prix_unitaire')


class PaiementInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = Paiement
    readonly_fields = ('mode', 'montant', 'statut', 'reference_externe', 'cree_le')


class LigneAchatInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = LigneAchat
    readonly_fields = ('medicament', 'quantite', 'prix_unitaire', 'recue')


class ReceptionAchatInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = ReceptionAchat
    readonly_fields = ('numero', 'recue_par', 'recue_le', 'commentaire')


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'telephone')
    fieldsets = UserAdmin.fieldsets + (('Profil PharmaGest', {'fields': ('role', 'telephone')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Profil PharmaGest', {'fields': ('role', 'telephone')}),)


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'description')
    search_fields = ('nom',)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'telephone', 'email', 'actif')
    list_filter = ('actif',)
    search_fields = ('nom', 'telephone', 'email')


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'contact_principal', 'telephone', 'email', 'actif')
    list_filter = ('actif',)
    search_fields = ('nom', 'contact_principal', 'telephone', 'email', 'identifiant_fiscal')


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = ('nom', 'denomination_generique', 'categorie', 'prix_vente', 'actif')
    list_filter = ('actif', 'categorie')
    search_fields = ('nom', 'denomination_generique', 'code_barres', 'laboratoire')
    list_select_related = ('categorie',)


@admin.register(LotStock)
class LotStockAdmin(admin.ModelAdmin):
    list_display = ('numero_lot', 'medicament', 'date_peremption', 'quantite', 'bloque')
    list_filter = ('bloque', 'date_peremption')
    search_fields = ('numero_lot', 'medicament__nom')
    list_select_related = ('medicament',)


@admin.register(CommandeAchat)
class CommandeAchatAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('numero', 'fournisseur', 'statut', 'cree_par', 'cree_le')
    list_filter = ('statut', 'cree_le')
    search_fields = ('numero', 'fournisseur__nom', 'cree_par__username')
    list_select_related = ('fournisseur', 'cree_par')
    inlines = (LigneAchatInline, ReceptionAchatInline)


@admin.register(LigneAchat)
class LigneAchatAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('commande', 'medicament', 'quantite', 'recue', 'prix_unitaire')
    search_fields = ('commande__numero', 'medicament__nom')
    list_select_related = ('commande', 'medicament')


@admin.register(ReceptionAchat)
class ReceptionAchatAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('numero', 'commande', 'recue_par', 'recue_le')
    date_hierarchy = 'recue_le'
    search_fields = ('numero', 'commande__numero', 'recue_par__username')
    list_select_related = ('commande', 'recue_par')


@admin.register(LigneReception)
class LigneReceptionAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('reception', 'ligne_achat', 'numero_lot', 'date_peremption', 'quantite')
    search_fields = ('reception__numero', 'numero_lot', 'ligne_achat__medicament__nom')
    list_select_related = ('reception', 'ligne_achat')


@admin.register(MouvementStock)
class MouvementStockAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('date_mouvement', 'type_mouvement', 'medicament', 'lot', 'quantite', 'utilisateur')
    list_filter = ('type_mouvement', 'date_mouvement')
    date_hierarchy = 'date_mouvement'
    search_fields = ('medicament__nom', 'reference', 'motif', 'utilisateur__username')
    list_select_related = ('medicament', 'lot', 'utilisateur')


@admin.register(Vente)
class VenteAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('numero', 'cree_le', 'client', 'caissier', 'statut', 'total')
    list_filter = ('statut', 'cree_le')
    date_hierarchy = 'cree_le'
    search_fields = ('numero', 'client__nom', 'caissier__username')
    list_select_related = ('client', 'caissier')
    inlines = (LigneVenteInline, PaiementInline)


@admin.register(LigneVente)
class LigneVenteAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('vente', 'medicament', 'lot', 'quantite', 'prix_unitaire')
    search_fields = ('vente__numero', 'medicament__nom', 'lot__numero_lot')
    list_select_related = ('vente', 'medicament', 'lot')


@admin.register(Paiement)
class PaiementAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('vente', 'cree_le', 'mode', 'montant', 'statut')
    list_filter = ('mode', 'statut', 'cree_le')
    date_hierarchy = 'cree_le'
    search_fields = ('vente__numero', 'reference_externe')
    list_select_related = ('vente',)


@admin.register(RetourVente)
class RetourVenteAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('vente', 'ligne_vente', 'quantite', 'remise_en_stock', 'remboursement', 'traite_par')
    list_filter = ('remise_en_stock', 'cree_le')
    date_hierarchy = 'cree_le'
    search_fields = ('vente__numero', 'ligne_vente__medicament__nom', 'traite_par__username')
    list_select_related = ('vente', 'ligne_vente', 'traite_par')


@admin.register(JournalAudit)
class JournalAuditAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('date_action', 'utilisateur', 'action', 'objet')
    list_filter = ('action', 'date_action')
    date_hierarchy = 'date_action'
    search_fields = ('utilisateur__username', 'action', 'objet', 'details')
    list_select_related = ('utilisateur',)


@admin.register(JournalRequete)
class JournalRequeteAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('date_requete', 'utilisateur', 'methode', 'chemin', 'statut', 'duree_ms')
    list_filter = ('methode', 'statut', 'date_requete')
    date_hierarchy = 'date_requete'
    search_fields = ('chemin', 'utilisateur__username')
    list_select_related = ('utilisateur',)


admin.site.site_header = 'PharmaGest · Supervision'
admin.site.site_title = 'PharmaGest Admin'
admin.site.index_title = 'Pilotage de l’application'
