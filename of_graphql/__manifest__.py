# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / GraphQL",
    'version': '16.0.2.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': "GraphQL pour OpenFire",
    'website': "https://www.openfire.fr",
    'depends': [
        'graphql_base',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'external_dependencies': {'python': ['graphene', 'graphdoc', 'graphql-server']},
    'installable': True,
    'application': False,
    'auto_install': False,
}
