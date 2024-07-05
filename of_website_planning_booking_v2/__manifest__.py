# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u"OpenFire / Prise de RDV en ligne v2",
    'version': '10.0.1.1.0',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'summary': u"Prise de RDV en ligne v2",
    'license': 'AGPL-3',
    'description': u"""
Module OpenFire pour la nouvelle prise de RDV en ligne depuis le site internet
==============================================================================
""",
    'website': u"www.openfire.fr",
    'depends': [
        'web',
        'of_planning_tournee',
        'of_service',
        'of_website_portal',
        'website_field_autocomplete',
    ],
    'data': [
        'data/of_website_planning_booking_v2_data.xml',
        'security/ir.model.access.csv',
        'security/of_website_planning_booking_v2_security.xml',
        'templates/of_website_planning_booking_v2_templates.xml',
        'views/of_planning_intervention_template_views.xml',
        'views/of_intervention_settings_views.xml',
        'views/of_planning_intervention_views.xml',
        'views/hr_employee_views.xml',
        'wizards/of_horaire_segment_wizard_views.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': False,
}
