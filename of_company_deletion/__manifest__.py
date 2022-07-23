# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Outil de suppression de société",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Outil de suppression de société et des objets associés
======================================================

Ce module met en place un outil permettant la suppression d'une société ainsi que de tous ses objets associés.

Voici l'ensemble des objets supprimés en même temps que la société :
    - Opportunités
    - Commandes de vente
    - Factures client
    - Paiements client
    - Remises en banque
    - Rapprochements bancaires
    - Bons de livraison
    - Partenaires
    - Commandes fournisseur
    - Bons de réception
    - Factures fournisseur
    - Paiements fournisseur
    - Autres paiements
    - Pièces comptables
    - Journaux
    - Taxes
    - Positions fiscales
    - Plan comptables
    - Comptes analytiques
    - Contrats analytiques
    - RDVs d'intervention
    - Demandes d'intervention
    - Contrats d'entretien
    - SAVs
    - Parcs installés
    - Entrepôts
    - Emplacements de stock
    - Mouvements de stock
    - Séquences
    - Utilisateurs
    - Employés
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_base',
    ],
    'data': [
        'views/templates.xml',
        'wizards/of_company_deletion_wizard_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
