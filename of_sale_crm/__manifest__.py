# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Sale CRM",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Personnalisation du CRM pour le module vente",
    'depends': [
        'of_sale',
        'of_crm',
        'of_product_brand',
    ],
    'data': [
        'data/of_crm_compute_date.xml',
        'data/ir_config_parameter.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/of_sale_followup_tag_views.xml',
        'views/crm_leads_views.xml',
        'views/mail_activity_type_views.xml',
        'views/of_crm_activity_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/of_add_attachment_activity_views.xml',
        'reports/sale_report_views.xml',
        'reports/account_invoice_report_views.xml',
    ],
    'installable': True,
}
