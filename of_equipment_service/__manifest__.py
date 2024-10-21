# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Équipements et demandes d'intervention",
    "version": "16.0.2.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "category": "OpenFire",
    "summary": "Module de lien entre les demandes d'intervention et les équipements",
    "website": "https://www.openfire.fr",
    "depends": [
        "of_equipment",
        "of_service",
    ],
    "data": [
        "data/of_service_request_type.xml",
        "data/of_service_request_stage.xml",
        "security/ir.model.access.csv",
        "views/of_service_request_stage_views.xml",
        "views/of_service_request_equipment_line_views.xml",
        "views/of_service_request_views.xml",
        "views/of_equipment_views.xml",
        "views/menuitems.xml",
        "wizards/of_equipment_link_create_wizard_views.xml",
        "reports/of_service_request_templates.xml",
    ],
    "qweb": [],
    "application": True,
    "installable": True,
    "auto_install": True,
}
