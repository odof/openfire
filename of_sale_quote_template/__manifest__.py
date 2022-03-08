# -*- coding: utf-8 -*-
{
    "name": "OpenFire / Modèle de devis",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': '',
    "category": "OpenFire",
    "description": u"""
Modèle de devis OpenFire
========================
Ce module ajoute les modèles de devis.

Module rétro-migré de Odoo 11.

Fonctionnalités
----------------
 - Ajout des modèles de devis
 - Ajout du menu Modèles de devis dans Ventes/Configuration/Ventes
 - Ajout d'un champ "Modèle de devis" sur les devis / bons de commande
 - Ajout d'un champ "Note d'insertion" sur les devis / bons de commande

Lors de la sélection d'un "Modèle de devis" sur le devis/bon de commande, celui-ci va se remplir automatiquement avec les informations du modèle.

Si une ligne d'article n'a pas pu être ajoutée, le champ 'Note d'insertion' apparaitra pour signaler l'utilisateur qu'il faut mettre à jour les informations du modèle.
""",
    "website": "www.openfire.fr",
    "depends": [
        "of_sale",
    ],
    "data": [
        'security/of_sale_security.xml',
        'security/ir.model.access.csv',
        'wizards/of_select_product_wizard_views.xml',
        'wizards/of_layout_category_wizard_views.xml',
        'wizards/of_layout_category_invoicing_wizard_views.xml',
        'wizards/of_sale_order_gestion_prix_wizard_views.xml',
        'views/of_sale_quote_template_views.xml',
        'views/sale_config_settings_views.xml',
        'views/of_sale_quote_template_templates.xml',
        'report/of_sale_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

