# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Planning d'intervention",
    "version": "16.0.1.4.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "Mise en place de la vue planning pour les interventions",
    "depends": [
        "of_planning",
        "of_web_planning_view",
        "base_geolocalize",
    ],
    "data": [
        "views/calendar_event_views.xml",
        "views/of_planning_intervention_template_views.xml",
        "views/menuitems.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "of_planning_view/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "uninstall_hook": "uninstall_hook",
}
