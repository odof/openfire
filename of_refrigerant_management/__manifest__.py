# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Gestion des fluides",
    'version': '16.0.1.1.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': "Gestion des fluides",
    'website': "https://www.openfire.fr",
    'depends': [
        'of_planning',
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/of_fluid_type_views.xml',
        'views/of_recovery_cylinder_views.xml',
        'views/of_fluid_transaction_views.xml', 
        'views/menuitems.xml',
        'data/data.xml',
    ],
    'qweb': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}
