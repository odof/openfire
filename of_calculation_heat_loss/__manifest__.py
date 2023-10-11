# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Calcul de déperdition de chaleur",
    'version': "10.0.3.0.0",
    'author': "OpenFire",
    'description': u"""
Gestion du calcul de déperdition de chaleur
===========================================
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_product_chem',
        'of_parc_installe',
        'of_calculation',
        'of_external',
        'website_form',
    ],
    'category': "OpenFire",
    'data': [
        'security/ir.model.access.csv',
        'data/of_calculation_heat_loss_data.xml',
        'data/of_calculation_altitude.xml',
        'data/of_calculation_base_temperature.xml',
        'data/of_calculation_base_temperature_line.xml',
        'data/of_calculation_construction_date.xml',
        'data/of_calculation_construction_type.xml',
        'data/of_calculation_fuel.xml',
        'data/of_calculation_department.xml',
        'data/of_calculation_surface.xml',
        'data/of_calculation_g.xml',
        'hooks/hook.xml',
        'views/of_calculation_heat_loss_views.xml',
        'views/of_calculation_heat_loss_line_views.xml',
        'views/of_calculation_surface_views.xml',
        'views/of_calculation_g_views.xml',
        'views/of_calculation_construction_type_views.xml',
        'views/of_calculation_fuel_views.xml',
        'views/of_calculation_fuel_consumption_views.xml',
        'views/of_parc_installe_views.xml',
        'views/sale_views.xml',
        'views/crm_lead_views.xml',
        'templates/assets.xml',
        'templates/heat_loss_calculation_form_templates.xml',
        'reports/of_calculation_heat_loss_report.xml',
        'reports/of_external_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
