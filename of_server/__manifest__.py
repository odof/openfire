# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Serveur",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'license': 'AGPL-3',
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Module OpenFire de fonctions serveur",
    'website': 'https://www.openfire.fr',
    'depends': [
        'web',
    ],
    'data': [
    ],
    'installable': False,  # Server-side module
    'application': False,
    'auto_install': False,
}
