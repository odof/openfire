# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / SMS",
    'version': "16.0.1.0.0",
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': "Module de SMS OpenFire",
    'website': "https://www.openfire.fr",
    'depends': [
        'sms_ovh_http',
        'of_base',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/of_sms_sender.xml',
        'views/of_sms_sender_views.xml',
        'views/res_partner_views.xml',
        'views/sms_sms_views.xml',
        'wizards/sms_composer_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
