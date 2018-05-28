# -*- coding: utf-8 -*-

{
    "name": "OpenFire Sale",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'category': 'OpenFire',
    "description": """
Personnalisation des ventes OpenFire
====================================

Modification de l'affichage du formulaire de devis/commande client.
Refonte de report.report_saleorder_document

Ajout d'un filtre de recherche pour les commandes à facturer entièrement.
Report de la description fabricant dans les devis et factures.

Modification du fonctionnement de l'outil de facturation pour les factures d'acompte :

- Une catégorie d'articles d'acompte est définie dans la configuration des ventes.
- La fenêtre de création de facture d'acompte propose la sélection d'un article appartenant à cette catégorie
- Si l'acompte est calculé en pourcentage de la commande, il s'agit désormais du pourcentage du montant TTC et non plus HT.
- Les taxes et le compte comptable des lignes d'acompte sont calculés selon les règles du module of_account_tax


Paramètres de ventes (sale.config.settings)
-------------------------------------------

- description paramètre (module(s) concerné(s))
- configuration de la catégorie des articles d'acompte (of_sale)
- inhibition avertissements de stock (of_sale_kit)
- inhibition affichage réf produit dans les rapports PDF (of_sale)
- redéfinition templates sale.report_saleorder_document, sale.report_invoice_document_inherit_sale et sale.report_invoice_layouted
""",
    "website": "www.openfire.fr",
    "depends": [
        "sale",
        "of_product",
        "of_base",
        "of_account_invoice_report",  # définition des paramètres d'adresse dans les rapports
        "of_account_tax",  # of_sale ajoute les modifications de of_account_tax dans la creation de facture d'acompte
    ],
    "data": [
        'views/of_sale_view.xml',
        'report/of_sale_report_templates.xml',
        'wizards/sale_make_invoice_advance_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
