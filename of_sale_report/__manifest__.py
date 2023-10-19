
{
    "name": "OpenFire / Rapports de vente",
    "version": "16.0.0.0.1",
    "author": "OpenFire",
    'license': '',
    "category": "OpenFire",
    "description": """
Rapports de vente OpenFire
==========================

- Ajout du champ date de pose dans les commandes
- Ajout du rapport de vente sur mesure

""",
    "website": "www.openfire.fr",
    "depends": [
        "of_purchase",
        "of_sale",
    ],
    "data": [
        'views/res_config_settings_views.xml',
        'views/sale_order_view.xml',
        'wizards/of_report_openflam_wizard.xml',
        'wizards/of_sale_order_verification_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
