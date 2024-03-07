# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Vue carte pour les clients et les fournisseurs",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Ajout d'un type de vue carte (OpenStreetMap) dans les clients et les fournisseurs",
    'depends': [
        'account',
        'of_map_view_partner',
    ],
    'data': ['views/res_partner_views.xml'],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': True,
    'uninstall_hook': '_uninstall_hook',
}
