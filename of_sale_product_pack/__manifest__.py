# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Ventes & Kits produits",
    "version": "16.0.1.1.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "summary": "Module de gestion de vente produits kits",
    "category": "OpenFire",
    "website": "https://www.openfire.fr",
    "depends": [
        "of_product_pack",
        "of_sale",
        "sale_product_pack",
    ],
    "data": [
        "views/sale_order_line_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
