# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Marge de vente",
    "version": "16.0.1.1.0",
    "author": "OpenFire",
    "license": "AGPL-3",
    "category": "OpenFire",
    "sequence": 15,
    "summary": "Module de gestion des marges de vente",
    "website": "https://www.openfire.fr",
    "depends": [
        "sale_margin",
        "of_sale",  # of_sale > of_account
    ],
    "data": [
        "security/res_groups.xml",
        "views/product_category_views.xml",
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
        "views/sale_order_line_views.xml",
        "views/product_template_views.xml",
        "wizards/of_sale_order_verification_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
