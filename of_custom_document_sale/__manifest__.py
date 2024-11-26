# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Rapports personnalisés pour les ventes",
    "version": "16.0.1.1.1",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "Documents",
    "summary": "Rapports personnalisés pour les ventes",
    "depends": [
        "of_custom_document",
        "of_sale",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/menuitems.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": True,
}
