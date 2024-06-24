# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / ESB",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "OpenFire Entreprise System Bus",
    'depends': [
        'queue_job',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/esb_security.xml',
        'data/ir_cron.xml',
        'views/esb_rule_views.xml',
        'views/esb_bus_views.xml',
        'views/esb_connection_views.xml',
        'views/esb_security_views.xml',
        'views/esb_service_views.xml',
        'views/esb_trigger_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
