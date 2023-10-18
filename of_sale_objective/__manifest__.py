# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Objectifs de vente",
    'version': '16.0.1.0.0',
    'license': "AGPL-3",
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Sale objectives",
    'depends': [
        'sale_management',
        'hr',
    ],
    'data': [
        'data/ir_config_parameter.xml',
        'security/ir.model.access.csv',
        'views/of_sale_objective_views.xml',
        'views/hr_employee_view.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
