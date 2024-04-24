# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Vue carte pour les clients (planning)",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Ajout de la vue carte (OpenStreetMap) pour les clients depuis les interventions",
    'depends': [
        'of_planning',
        'of_map_view_partner',
    ],
    'data': [],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': True,
    'post_init_hook': '_post_init_hook',
    'uninstall_hook': '_uninstall_hook',
}
