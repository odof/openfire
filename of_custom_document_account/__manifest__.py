# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'OpenFire / Rapports personnalisés pour les factures clients/fournisseurs',
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "Documents",
    'summary': "Rapports personnalisés pour les factures clients/fournisseurs",
    'depends': ['of_custom_document', 'of_sale'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
