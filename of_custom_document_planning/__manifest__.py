# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Rapports personnalisés pour les interventions",
    "version": "16.0.1.0.1",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "Documents",
    "summary": "Rapports personnalisés pour les interventions",
    "depends": [
        "of_custom_document",
        "of_planning",
    ],
    "data": [
        "data/of_planning_intervention_template.xml",
        "views/calendar_event_views.xml",
        "views/of_planning_intervention_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": True,
}
