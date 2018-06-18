# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#
##############################################################################

{
    'name' : u"OpenFire / Ventes",
    'version' : "10.0.1.0.0",
    'license': '',
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Module OpenFlam",
    'summary': u"Personnalisation des ventes OpenFire",
    'description': u"""

Module OpenFire - Ventes
========================

Modification de l'affichage du formulaire de devis/commande client.
Refonte de report.report_saleorder_document

Ajout d'un filtre de recherche pour les commandes à facturer entièrement.
Report de la description fabricant dans les devis et factures.

Modification du fonctionnement de l'outil de facturation pour les factures d'acompte :
- Une catégorie d'articles d'acompte est définie dans la configuration des ventes.
- La fenêtre de création de facture d'acompte propose la sélection d'un article appartenant à cette catégorie
- Si l'acompte est calculé en pourcentage de la commande, il s'agit désormais du pourcentage du montant TTC et non plus HT.
- Les taxes et le compte comptable des lignes d'acompte sont calculés selon les règles du module of_account_tax

Permettre d'ajouter des documents joints dans l'impression des devis/commandes

Outil de gestion des prix
-------------------------

Ajout d'un bouton depuis le bon de commande permettant l'accès à diverses informations et fonctionnalités.

- Affichage de la marge
- Possibilité de modifier le prix de vente total de la commande :
- - en choisissant un montant cible
- - en choisissant une marge cible
- - en remettant les articles au prix magasin

Ces actions sont effectuables pour l'ensemble de la commande ou sur une sélection de lignes.


Paramètres de ventes (sale.config.settings)
-------------------------------------------

- description paramètre (module(s) concerné(s))
- configuration de la catégorie des articles d'acompte (of_sale)
- inhibition avertissements de stock (of_sale_kit)
- inhibition affichage réf produit dans les rapports PDF (of_sale)
- redéfinition templates sale.report_saleorder_document, sale.report_invoice_document_inherit_sale et sale.report_invoice_layouted

""",
    'depends' : [
        "of_account_invoice_report",  # définition des paramètres d'adresse dans les rapports
        "of_account_tax",  # of_sale ajoute les modifications de of_account_tax dans la creation de facture d'acompte
        "of_base",
        "of_gesdoc",
        "of_product",
        "sale",
    ],
    'external_dependancies': {
        'python': ['pdfminer', 'pypdftk', 'pyPdf'],
    },
    'data' : [
        'views/of_sale_view.xml',
        'report/of_sale_report_templates.xml',
        'wizards/of_sale_order_gestion_prix_views.xml',
        'wizards/sale_make_invoice_advance_views.xml',
    ],
    'active': True,
    'installable': True,
    'application': False,
    'auto_install': False,
}
