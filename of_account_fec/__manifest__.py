# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / FEC",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Modue d'extension de l10n_fr_fec",
    'website': 'https://www.openfire.fr',
    'description': "",
    'depends': [
        'l10n_fr_fec',
    ],
    'data': [
        'wizard/of_account_fec_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
