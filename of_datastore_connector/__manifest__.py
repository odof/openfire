# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "OpenFire / Connecteur Odoo",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'website': 'http://www.openfire.fr',
    'category': 'Openfire',
    'description': """""",
    'depends': [
        'of_base'
    ],
    'external_dependencies': {
        'python': [
            'openerp-client-lib'
        ],
    },
    'data': [
        'views/of_datastore_connector_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
