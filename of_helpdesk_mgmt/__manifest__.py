# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Helpdesk Management",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'website': 'https://www.openfire.fr',
    'depends': [
        'helpdesk_mgmt',
        'of_crm',
        'of_equipment_service',
    ],
    'data': [
        'views/helpdesk_ticket_views.xml',
        'views/crm_lead_views.xml',
        'views/of_service_request_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
