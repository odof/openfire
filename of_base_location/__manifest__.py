# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Géolocalisation des communes",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': 'OpenFire',
    'summary': "Extension module for base_location",
    'description': "",
    'depends': [
        'of_base',
        'base_location_geonames_import',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_city_zip_views.xml',
        'views/of_sector_views.xml',
        'views/res_partner_views.xml',
        'wizards/of_res_partner_assign_sector_wizard_views.xml',
        'wizards/of_res_partner_update_sector_wizard_views.xml',
        'wizards/of_secteur_update_delete_wizard_views.xml',
    ],
    'installable': True,
}
