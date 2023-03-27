# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Multi-logos",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Gestion des multi-logos",
    'website': "https://www.openfire.fr",
    'description': "",
    'depends': [
        'web',
        'of_base',
    ],
    'data': [
        'data/report_paperformat_data.xml',
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/of_company_multi_logos_views.xml',
        'views/menuitems.xml',
        'report/report_templates.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
