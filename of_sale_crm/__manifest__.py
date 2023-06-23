
{
    'name': "OpenFire / CRM",
    'version': "10.0.1.3.0",
    'author': "OpenFire",
    'website': "http://openfire.fr",
    'category': 'Customer Relationship Management',
    'license': "AGPL-3",
    'depends': [
        'of_sale',
        'of_crm',
    ],
    'data': [
        'reports/account_invoice_report_views.xml',
        'reports/sale_report_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/of_sale_followup_tag_views.xml',
        'views/crm_leads_views.xml',
        'views/mail_activity_type_views.xml'
    ],
    'qweb': [
        'static/src/xml/of_sales_team_dashboard.xml',
        'wizards/of_add_attachment_activity_views.xml',
    ],
    'installable': True,
}
