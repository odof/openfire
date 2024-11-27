# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Planning d'intervention / Congés",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "Mise en place des avertissements congés dans la vue planning pour les interventions",
    "depends": [
        "of_planning_view",
        "hr_holidays",
    ],
    "data": [
        "views/calendar_event_views.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": True,
}
