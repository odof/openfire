# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / ESB Operating Data",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "OpenFire Entreprise Service Bus - Operating Data",
    'depends': [
        'of_esb',
        'of_esb_odoo',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/of_esb_type_bus.xml',
        'views/of_esb_trigger.xml',
        'views/of_esb_extract.xml',
        'views/of_esb_transform.xml',
        'views/of_esb_load.xml',
        'wizards/wizard_esb_export.xml',
        'wizards/wizard_esb_import.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
