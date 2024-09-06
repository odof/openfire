{
    'name': "OpenFire / SMS",
    'version': "16.0.0.0.0",
    'author': "OpenFire",
    'license': 'LGPL-3',
    'website': "www.openfire.fr",
    'category': "Generic Modules/",
    'description': """
Module de SMS OpenFire
======================

- Envoi de SMS depuis les partenaires instantanément ou en différé
""",
    'depends': [
        'sms_ovh_http',
        'of_base',
        'mail',
    ],
    'demo_xml': [],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/of_sms_sender_views.xml',
        'views/res_partner_views.xml',
        'views/sms_sms_views.xml',
        'wizard/sms_composer_views.xml',
    ],
    'installable': True,
}
