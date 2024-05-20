# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / OF Base GraphQL",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': "Ajoute les données de base odoo dans le schéma Graphql",
    'website': "https://www.openfire.fr",
    'depends': [
        'of_graphql',
        'graphql_base',
        'of_base',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': True,
}
