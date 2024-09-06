{
    'name': "OpenFire / SMS Planning",
    'version': "16.0.0.0.0",
    'author': "OpenFire",
    'license': 'LGPL-3',
    'website': "www.openfire.fr",
    'category': "Generic Modules/",
    'description': u"""
Module de SMS OpenFire pour le planning
=======================================

- Envoi de SMS depuis le planning d'intervention instantanément ou en différé
- Tâche automatique journalière envoyant des textos de rappel la veille aux équipes d'intervention et/ou aux clients
""",
    'depends': [
        'of_sms',
        'of_planning',
    ],
    'demo_xml': [],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/sms_template.xml',
        'views/calendar_event_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
}
