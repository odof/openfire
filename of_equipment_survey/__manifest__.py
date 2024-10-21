# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Questionnaires équipement",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "category": "OpenFire",
    "summary": "Module de liaison entre les équipements et les questionnaires",
    "website": "https://www.openfire.fr",
    "depends": [
        "of_equipment",
        "of_survey",
        # explicit dependency : `of_planning_survey` is in `auto_install` and depends on `of_planning` and
        # `of_equipment` and we wants to make sure that `of_planning_survey` is installed before this module.
        "of_planning_survey",
    ],
    "data": [
        "data/of_equipment_intervention_report_template.xml",
        "views/of_equipment_intervention_report_template_views.xml",
        "views/of_planning_survey_views.xml",
        "views/of_calendar_event_equipment_link_views.xml",
        "reports/report_equipment.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": True,
    "uninstall_hook": "uninstall_hook",
}
