# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Connecteur commun - achats/ventes",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "Module commun pour les connecteurs achats/ventes",
    "depends": [
        "of_datastore_connector",
        "of_sale",
        "purchase",
        "stock",
    ],
    "data": [
        "views/purchase_views.xml",
        "views/picking_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
