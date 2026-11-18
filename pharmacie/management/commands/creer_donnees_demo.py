from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from pharmacie.models import (
    Categorie,
    Client,
    CommandeAchat,
    Fournisseur,
    LigneAchat,
    LotStock,
    Medicament,
    Paiement,
    ReceptionAchat,
)
from pharmacie.services import effectuer_vente, receptionner_ligne


class Command(BaseCommand):
    help = "Crée un compte administrateur et des données de démonstration."

    @transaction.atomic
    def handle(self, *args, **opts):
        User = get_user_model()
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@pharmagest.local",
                "role": "ADMIN",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("Admin12345")
            admin.save(update_fields=["password"])

        demo_users = {}
        for username, role in (
            ("demo_pharmacien", "PHARMACIEN"),
            ("demo_stock", "STOCK"),
            ("demo_caissier", "CAISSIER"),
            ("demo_gestion", "GESTION"),
        ):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@pharmagest.local", "role": role},
            )
            if created:
                user.set_password("Demo12345")
                user.save(update_fields=["password"])
            demo_users[username] = user

        categories = {}
        for name in ("Antalgiques", "Vitamines", "Digestifs", "Dermatologie", "ORL"):
            categories[name], _ = Categorie.objects.get_or_create(nom=name)

        supplier_data = (
            ("Grossiste Santé Mada", "0340000000", "contact@example.mg"),
            ("Pharma Distribution", "0340000001", "ventes@distribution.example.mg"),
            ("Laboratoire Central", "0340000002", "commandes@laboratoire.example.mg"),
        )
        suppliers = {}
        for name, telephone, email in supplier_data:
            suppliers[name], _ = Fournisseur.objects.get_or_create(
                nom=name,
                defaults={"telephone": telephone, "email": email, "actif": True},
            )

        med_data = (
            ("Paracétamol 500 mg", "Antalgiques", "Paracétamol", "500 mg", 150, 250),
            ("Vitamine C 500 mg", "Vitamines", "Acide ascorbique", "500 mg", 300, 500),
            ("Ibuprofène 200 mg", "Antalgiques", "Ibuprofène", "200 mg", 250, 400),
            ("Aspirine 100 mg", "Antalgiques", "Acide acétylsalicylique", "100 mg", 200, 350),
            ("Vitamine D3 1000 UI", "Vitamines", "Cholécalciférol", "1000 UI", 400, 650),
            ("Solution de réhydratation orale", "Digestifs", "Sels de réhydratation", "sachet", 350, 600),
            ("Crème antiseptique 1%", "Dermatologie", "Antiseptique", "1%", 800, 1200),
            ("Sérum physiologique 5 ml", "ORL", "Chlorure de sodium", "5 ml", 100, 200),
            ("Sirop antitussif 120 ml", "ORL", "Sirop antitussif", "120 ml", 1200, 1800),
            ("Oméprazole 20 mg", "Digestifs", "Oméprazole", "20 mg", 500, 800),
        )
        medicines = {}
        for name, category, generic, dosage, purchase_price, sale_price in med_data:
            medicines[name], _ = Medicament.objects.get_or_create(
                nom=name,
                defaults={
                    "categorie": categories[category],
                    "denomination_generique": generic,
                    "forme": "Comprimé" if "mg" in dosage else "Unité",
                    "dosage": dosage,
                    "laboratoire": "Laboratoire Démo",
                    "prix_achat": purchase_price,
                    "prix_vente": sale_price,
                    "seuil_alerte": 5,
                },
            )

        client_data = (
            ("Client Démo 01", "0341000001"),
            ("Client Démo 02", "0341000002"),
            ("Client Démo 03", "0341000003"),
            ("Client Démo 04", "0341000004"),
            ("Client Démo 05", "0341000005"),
            ("Client Démo 06", "0341000006"),
        )
        clients = {}
        for name, telephone in client_data:
            clients[name], _ = Client.objects.get_or_create(
                nom=name,
                defaults={
                    "telephone": telephone,
                    "email": f"{telephone}@clients.example.mg",
                    "adresse": "Antananarivo",
                    "actif": True,
                },
            )

        purchase_orders = (
            (
                "DEMO-A-001",
                "Grossiste Santé Mada",
                (
                    ("Paracétamol 500 mg", 80),
                    ("Vitamine C 500 mg", 60),
                    ("Ibuprofène 200 mg", 50),
                    ("Aspirine 100 mg", 45),
                    ("Vitamine D3 1000 UI", 40),
                ),
            ),
            (
                "DEMO-A-002",
                "Laboratoire Central",
                (
                    ("Solution de réhydratation orale", 40),
                    ("Crème antiseptique 1%", 30),
                    ("Sérum physiologique 5 ml", 60),
                    ("Sirop antitussif 120 ml", 25),
                    ("Oméprazole 20 mg", 50),
                ),
            ),
        )
        today = timezone.localdate()
        for order_number, supplier_name, items in purchase_orders:
            order, _ = CommandeAchat.objects.get_or_create(
                numero=order_number,
                defaults={
                    "fournisseur": suppliers[supplier_name],
                    "cree_par": demo_users["demo_stock"],
                    "statut": "COMMANDEE",
                    "valide_le": timezone.now(),
                },
            )
            reception, _ = ReceptionAchat.objects.get_or_create(
                numero=order_number.replace("A-", "R-"),
                defaults={"commande": order, "recue_par": demo_users["demo_stock"]},
            )
            for index, (medicine_name, quantity) in enumerate(items, start=1):
                medicine = medicines[medicine_name]
                line, _ = LigneAchat.objects.get_or_create(
                    commande=order,
                    medicament=medicine,
                    defaults={
                        "quantite": quantity,
                        "prix_unitaire": medicine.prix_achat,
                    },
                )
                remaining = line.quantite - line.recue
                if remaining > 0:
                    receptionner_ligne(
                        line,
                        remaining,
                        f"{order_number}-LOT-{index:02d}",
                        today + timedelta(days=365 + index),
                        reception,
                        demo_users["demo_stock"],
                    )

        sales = (
            ("Client Démo 01", "Paracétamol 500 mg", 2, "ESPECES"),
            ("Client Démo 02", "Vitamine C 500 mg", 1, "MOBILE_MONEY"),
            ("Client Démo 03", "Ibuprofène 200 mg", 2, "CARTE"),
            ("Client Démo 04", "Sérum physiologique 5 ml", 3, "ESPECES"),
            ("Client Démo 05", "Oméprazole 20 mg", 1, "MOBILE_MONEY"),
        )
        cashier = demo_users["demo_caissier"]
        for index, (client_name, medicine_name, quantity, payment_mode) in enumerate(sales, start=1):
            reference = f"DEMO-PAIEMENT-{index:03d}"
            if Paiement.objects.filter(reference_externe=reference).exists():
                continue
            effectuer_vente(
                cashier,
                [{"medicament_id": medicines[medicine_name].pk, "quantite": quantity}],
                mode_paiement=payment_mode,
                client=clients[client_name],
                reference=reference,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Données de démonstration créées : 10 médicaments, 6 clients, "
                "3 fournisseurs, 2 achats réceptionnés et 5 ventes."
            )
        )
        self.stdout.write("Comptes de démonstration : admin / Admin12345, "
                          "demo_pharmacien, demo_stock, demo_caissier, demo_gestion / Demo12345")
