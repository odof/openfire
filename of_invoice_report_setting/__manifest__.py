# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Paramétrage du rapport de facture",
    'author': "OpenFire",
    'version': '16.0.1.1.0',
    'license': 'LGPL-3',
    'category': 'OpenFire',
    'summary': "Print options for Invoice report",
    'website': 'https://www.openfire.fr',
    'depends': [
        'of_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/of_invoice_document_layout_views.xml',
        'views/res_config_settings_views.xml',
        'report/of_invoice_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
