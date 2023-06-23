
{
    'name': "OpenFire / Sale Objective",
    'version': "10.0.1.3.0",
    'author': "OpenFire",
    'website': "http://openfire.fr",
    'category': 'Customer Relationship Management',
    'license': "AGPL-3",
    'depends': [
        'sale',
    ],
    'data': [
        'views/of_sale_objective_views.xml',
    ],
    'qweb': [
        'static/src/xml/of_sales_team_dashboard.xml',
    ],
    'installable': True,
}
