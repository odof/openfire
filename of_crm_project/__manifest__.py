# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Projets CRM",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Projets CRM",
    'depends': [
        'of_crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/of_crm_security.xml',
        'views/of_crm_project_attr_select_views.xml',
        'views/of_crm_project_attr_views.xml',
        'views/of_crm_project_line_views.xml',
        'views/of_crm_project_views.xml',
        'views/crm_lead_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
}
