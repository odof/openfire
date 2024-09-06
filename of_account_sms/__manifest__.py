{
    'name': "OpenFire / SMS Account",
    'version': "16.0.0.0.0",
    'author': "OpenFire",
    'license': 'LGPL-3',
    'website': "www.openfire.fr",
    'category': "Generic Modules/",
    'description': u"""
Module de SMS OpenFire pour la comptabilité
===========================================

- Envoi de SMS depuis la comptabilité instantanément ou en différé
""",
    'depends': [
        'of_sms',
        'of_account',
    ],
    'demo_xml': [],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
}
