# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Impression totaux des factures",
    'version': '16.0.1.1.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'website': 'https://www.openfire.fr',
    'category': 'OpenFire',
    'summary': "Affichage des totaux dans les factures",
    'depends': [
        'of_invoice_report_setting',
    ],
    'data': [
        'data/of_invoice_report_data.xml',
        'security/ir.model.access.csv',
        'report/of_invoice_report_templates.xml',
        'views/of_invoice_report_total_group_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
