# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Migration",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Migration module for OpenFire",
    'website': 'https://www.openfire.fr',
    'depends': [
        'base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/migration_database.xml',
        'views/migration_migration.xml',
        'views/migration_server.xml',
        'views/migration_sql.xml',
        'views/migration_authentication.xml',
        'views/res_partner.xml',
        'views/menus.xml',
        'wizards/wizard_create_migration.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
}
