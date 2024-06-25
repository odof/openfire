# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / OF Sale CRM GraphQL",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': "Ajoute les données de of_sale_crm dans le schéma Graphql",
    'website': "https://www.openfire.fr",
    'depends': [
        'of_sale',
        'of_sale_graphql',
        'of_sale_crm',
        'of_base_graphql',
    ],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': True,
}
