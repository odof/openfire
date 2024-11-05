# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Données techniques / Normes produits",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "category": "OpenFire",
    "summary": "Module de lien entre les données techniques et les normes produit",
    "website": "https://www.openfire.fr",
    "depends": [
        "of_sale_product_standard",
        "of_industry",
    ],
    "data": [
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": True,
    "uninstall_hook": "uninstall_hook",
}
