# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'OpenFire / Rapports personnalisés pour les équipements',
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "Documents",
    'summary': "Rapports personnalisés pour les équipements",
    'depends': [
        'of_custom_document',
        'of_equipment'
    ],
    'data': [
        'views/of_equipment_intervention_report_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
