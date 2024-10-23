# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "OpenFire / module spécifique Wizville",
    'version': "16.0.1.0.0",
    'author': "OpenFire",
    'category': "OpenFire",

    'website': "www.openfire.fr",
    'depends': [
        'of_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/of_sanitize_query.xml',
        'data/of_wizville_data.xml',
        'views/of_connector_config_settings_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/of_wizville_history_views.xml',
        'views/menuitems.xml',
        ],
    'qweb': [
    ],
    # Ce module necessite à installer la biblio "paramiko"
    'installable': True,
    'application': False,
    'auto_install': False,
}
