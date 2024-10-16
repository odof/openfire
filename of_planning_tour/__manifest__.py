# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Planning des tournées",
    'version': '16.0.1.1.4',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Planning des tournées et optimisation d'itinéraire",
    'depends': [
        'of_service',  # of_planning > of_sale_stock > of_sale_report_settings > of_sale > ... > of_base > of_web_widgets
    ],
    'data': [
        'data/ir_cron.xml',
        'data/ir_config_parameter.xml',
        'data/ir_action_server.xml',
        'security/ir.model.access.csv',
        'security/of_planning_tour_security.xml',
        'views/calendar_event_views.xml',
        'views/of_planning_available_slot_views.xml',
        'views/of_planning_tour_views.xml',
        'views/of_planning_tour_line_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        'views/of_tour_appointment_template_views.xml',
        'wizards/of_tour_appointment_wizard_views.xml',
        'wizards/tour_planning_optimization_views.xml',
        'wizards/tour_planning_reorganization_views.xml',
        'wizards/tour_planning_mass_sector_assignation_views.xml',
        'wizards/tour_planning_mass_route_update_views.xml',
        'views/menuitems.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'of_planning_tour/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
