from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import (
    Categorie,
    Client,
    CommandeAchat,
    Fournisseur,
    JournalAudit,
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


admin.site.site_header = "PharmaGest · Supervision"
admin.site.site_title = "PharmaGest Admin"
admin.site.index_title = "Pilotage de l’application"


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        return tuple(self.readonly_fields) + tuple(
            field.name for field in self.model._meta.fields
        )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class LigneAchatInline(ReadOnlyInline):
    model = LigneAchat
    fields = ("medicament", "quantite", "recue", "prix_unitaire")


class ReceptionAchatInline(ReadOnlyInline):
    model = ReceptionAchat
    fields = ("numero", "recue_par", "recue_le", "commentaire")


class LigneReceptionInline(ReadOnlyInline):
    model = LigneReception
    fields = ("ligne_achat", "numero_lot", "date_peremption", "quantite")


class LigneVenteInline(ReadOnlyInline):
    model = LigneVente
    fields = ("medicament", "lot", "quantite", "prix_unitaire", "sous_total")
    readonly_fields = ("sous_total",)


class PaiementInline(ReadOnlyInline):
    model = Paiement
    fields = ("mode", "statut", "montant", "reference_externe", "cree_le")


class RetourVenteInline(ReadOnlyInline):
    model = RetourVente
    fields = (
        "ligne_vente",
        "quantite",
        "motif",
        "remise_en_stock",
        "remboursement",
        "traite_par",
        "cree_le",
    )


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "role",
        "is_active",
        "is_staff",
        "last_login",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "first_name", "last_name", "email", "telephone")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + (
        ("Profil PharmaGest", {"fields": ("role", "telephone")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Profil PharmaGest", {"fields": ("role", "telephone")}),
    )


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ("nom", "medicament_count")
    search_fields = ("nom", "description")
    ordering = ("nom",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _medicament_count=Count("medicaments", distinct=True)
        )

    @admin.display(description="Médicaments", ordering="_medicament_count")
    def medicament_count(self, obj):
        return obj._medicament_count


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "categorie",
        "dosage",
        "prix_achat",
        "prix_vente",
        "stock_disponible_actuel",
        "actif",
    )
    list_filter = ("actif", "categorie")
    search_fields = ("nom", "denomination_generique", "code_barres", "laboratoire")
    list_select_related = ("categorie",)
    ordering = ("nom",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("categorie").annotate(
            _stock_disponible=Sum(
                "lots__quantite",
                filter=Q(
                    lots__bloque=False,
                    lots__date_peremption__gte=timezone.localdate(),
                ),
            )
        )

    @admin.display(description="Stock disponible", ordering="_stock_disponible")
    def stock_disponible_actuel(self, obj):
        return obj._stock_disponible or 0


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "email", "contact_principal", "actif")
    list_filter = ("actif",)
    search_fields = ("nom", "telephone", "email", "identifiant_fiscal")
    ordering = ("nom",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "email", "actif")
    list_filter = ("actif",)
    search_fields = ("nom", "telephone", "email")
    ordering = ("nom",)


@admin.register(LotStock)
class LotStockAdmin(admin.ModelAdmin):
    list_display = ("medicament", "numero_lot", "date_peremption", "quantite", "bloque", "perime")
    list_filter = ("bloque", "date_peremption")
    search_fields = ("medicament__nom", "numero_lot")
    list_select_related = ("medicament",)
    date_hierarchy = "date_peremption"
    ordering = ("date_peremption",)

    @admin.display(boolean=True, description="Périmé")
    def perime(self, obj):
        return obj.perime


class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return tuple(self.readonly_fields) + tuple(
            field.name for field in self.model._meta.fields
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CommandeAchat)
class CommandeAchatAdmin(ReadOnlyAdmin):
    list_display = ("numero", "fournisseur", "statut", "total_affiche", "cree_par", "cree_le")
    list_filter = ("statut", "cree_le")
    search_fields = ("numero", "fournisseur__nom", "cree_par__username")
    list_select_related = ("fournisseur", "cree_par")
    date_hierarchy = "cree_le"
    ordering = ("-cree_le",)
    inlines = (LigneAchatInline, ReceptionAchatInline)

    @admin.display(description="Total")
    def total_affiche(self, obj):
        return obj.total


@admin.register(LigneAchat)
class LigneAchatAdmin(ReadOnlyAdmin):
    list_display = ("commande", "medicament", "quantite", "recue", "prix_unitaire")
    list_filter = ("commande__statut",)
    search_fields = ("commande__numero", "medicament__nom")
    list_select_related = ("commande", "medicament")


@admin.register(ReceptionAchat)
class ReceptionAchatAdmin(ReadOnlyAdmin):
    list_display = ("numero", "commande", "recue_par", "recue_le")
    list_filter = ("recue_le",)
    search_fields = ("numero", "commande__numero", "recue_par__username")
    list_select_related = ("commande", "recue_par")
    date_hierarchy = "recue_le"
    inlines = (LigneReceptionInline,)


@admin.register(LigneReception)
class LigneReceptionAdmin(ReadOnlyAdmin):
    list_display = ("reception", "ligne_achat", "numero_lot", "date_peremption", "quantite")
    list_filter = ("date_peremption",)
    search_fields = ("reception__numero", "numero_lot", "ligne_achat__medicament__nom")
    list_select_related = ("reception", "ligne_achat")


@admin.register(MouvementStock)
class MouvementStockAdmin(ReadOnlyAdmin):
    list_display = ("date_mouvement", "medicament", "type_mouvement", "quantite", "reference", "utilisateur")
    list_filter = ("type_mouvement", "date_mouvement")
    search_fields = ("medicament__nom", "lot__numero_lot", "reference", "motif", "utilisateur__username")
    list_select_related = ("medicament", "lot", "utilisateur")
    date_hierarchy = "date_mouvement"
    ordering = ("-date_mouvement",)


@admin.register(Vente)
class VenteAdmin(ReadOnlyAdmin):
    list_display = ("numero", "cree_le", "client", "caissier", "statut", "total")
    list_filter = ("statut", "cree_le")
    search_fields = (
        "numero",
        "client__nom",
        "caissier__username",
        "lignes__medicament__nom",
        "paiements__reference_externe",
    )
    list_select_related = ("client", "caissier")
    date_hierarchy = "cree_le"
    ordering = ("-cree_le",)
    inlines = (LigneVenteInline, PaiementInline, RetourVenteInline)


@admin.register(LigneVente)
class LigneVenteAdmin(ReadOnlyAdmin):
    list_display = ("vente", "medicament", "lot", "quantite", "prix_unitaire", "sous_total")
    list_filter = ("vente__statut",)
    search_fields = ("vente__numero", "medicament__nom", "lot__numero_lot")
    list_select_related = ("vente", "medicament", "lot")


@admin.register(Paiement)
class PaiementAdmin(ReadOnlyAdmin):
    list_display = ("vente", "mode", "statut", "montant", "reference_externe", "cree_le")
    list_filter = ("mode", "statut", "cree_le")
    search_fields = ("vente__numero", "reference_externe")
    list_select_related = ("vente",)
    date_hierarchy = "cree_le"


@admin.register(RetourVente)
class RetourVenteAdmin(ReadOnlyAdmin):
    list_display = ("vente", "ligne_vente", "quantite", "remise_en_stock", "remboursement", "traite_par", "cree_le")
    list_filter = ("remise_en_stock", "cree_le")
    search_fields = ("vente__numero", "ligne_vente__medicament__nom", "motif", "traite_par__username")
    list_select_related = ("vente", "ligne_vente", "traite_par")
    date_hierarchy = "cree_le"


@admin.register(JournalAudit)
class JournalAuditAdmin(ReadOnlyAdmin):
    list_display = ("date_action", "utilisateur", "action", "objet", "adresse_ip")
    list_filter = ("action", "date_action")
    search_fields = ("action", "objet", "details", "utilisateur__username")
    list_select_related = ("utilisateur",)
    date_hierarchy = "date_action"
    ordering = ("-date_action",)
