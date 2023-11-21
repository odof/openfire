# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Geolocalisation",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Module d'extension de la géolocalisation des partenaires",
    'depends': [
        'contacts',
        'base_geolocalize',
    ],
    'data': [
        'data/ir_config_parameter.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'wizards/of_geo_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
