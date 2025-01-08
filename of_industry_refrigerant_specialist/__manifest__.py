# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Données techniques - Climaticien",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "category": "OpenFire",
    "summary": "Gestion des données techniques des climaticiens",
    "website": "https://www.openfire.fr",
    "depends": [
        "of_industry",
    ],
    "data": [
        "data/data.xml",
        "data/of_fluid_nature_data.xml",
        "views/product_template_views.xml",
        "views/of_fluid_nature_views.xml",
        "views/menuitems.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
