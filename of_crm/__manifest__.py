# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / CRM",
    "version": "16.0.1.4.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "Personnalisation du CRM",
    "depends": [
        "crm",
        "of_base_location",  # -> of_base
        "of_utm",
        "of_utils",
        "of_geolocalize",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_stage_views.xml",
        "views/crm_lead_views.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/mail_activity_type_views.xml",
        "views/utm_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}
