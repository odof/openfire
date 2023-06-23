
{
    'name': "OpenFire / CRM",
    'version': "10.0.1.3.0",
    'author': "OpenFire",
    'website': "http://openfire.fr",
    'category': 'Customer Relationship Management',
    'license': "AGPL-3",
    'depends': [
        'sale_crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/of_crm_funnel_conversion_views.xml',
        'reports/of_invoiced_revenue_analysis.xml',
    ],
    'qweb': [
        'static/src/xml/of_sales_team_dashboard.xml',
    ],
    'installable': True,
}
