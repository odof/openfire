
{
    'name': "OpenFire / CRM",
    'version': "10.0.1.3.0",
    'author': "OpenFire",
    'website': "http://openfire.fr",
    'category': 'Customer Relationship Management',
    'license': "AGPL-3",
    'depends': [
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/of_crm_security.xml',
        'views/crm_lead_views.xml',
    ],
    'qweb': [
        'static/src/xml/of_sales_team_dashboard.xml',
    ],
    'installable': True,
}
