# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Vue carte pour la vue planning",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Ajout de la vue carte (OpenStreetMap) pour la vue planning",
    'depends': [
        'of_planning_view',
        'of_map_view',
    ],
    'data': [
        'data/data.xml',
        ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': True,
    'uninstall_hook': '_uninstall_hook',
}
