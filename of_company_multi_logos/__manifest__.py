# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Multi-logos",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Gestion des multi-logos",
    'website': "https://www.openfire.fr",
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
    # NOTE : Standard functionality should be enough now we are waiting for internal feedback.
    # If its ok just delete this module, otherwise we will need keep it installable.
    'installable': False,
    'application': False,
    'auto_install': False,
}
