# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Données techniques équipements - Climaticien",
    "version": "16.0.1.1.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "category": "OpenFire",
    "summary": "Gestion des données techniques des climaticiens sur les equipements",
    "website": "https://www.openfire.fr",
    "depends": [
        "of_equipment",
        "of_equipment_industry",
        "of_industry_refrigerant_specialist",
    ],
    "data": [
        "views/of_equipment_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
