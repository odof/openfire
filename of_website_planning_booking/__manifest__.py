# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Prise de RDV en ligne",
    "version": "16.0.1.1.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "category": "OpenFire",
    "summary": "Prise de RDV en ligne",
    "website": "https://www.openfire.fr",
    "depends": [
        "of_planning_tour",
        "of_service",
        "website",
    ],
    "data": [
        "data/mail_template.xml",
        "data/website_menu.xml",
        "security/ir.model.access.csv",
        "security/of_website_planning_booking_security.xml",
        "templates/of_website_planning_booking_templates.xml",
        "views/calendar_event_views.xml",
        "views/hr_employee_views.xml",
        "views/of_planning_available_slot_views.xml",
        "views/of_planning_intervention_template_views.xml",
        "views/of_planning_tour_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "of_website_planning_booking/static/src/scss/heading_label.scss",
        ],
        "web.assets_frontend": [
            "of_website_planning_booking/static/src/xml/of_booking_slot_kanban.xml",
            "of_website_planning_booking/static/src/js/of_website_planning_booking.js",
            "of_website_planning_booking/static/src/scss/of_website_planning_booking.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}
