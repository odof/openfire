# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Planning x Google",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Generic Modules",
    'summary': u"Interventions x Google agenda",
    'description': u"""
Ce module permet de synchroniser le planning d'interventions avec Google agenda
===============================================================================

l'activation se fait via la configuration des interventions.

Une fois activée, un bouton "synchronisez avec Google" apparait dans le calendrier des interventions.
""",
    'depends': [
        'google_calendar',
        'of_planning_recurring',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'data': [
        'data/of_planning_google_data.xml',
        'security/of_planning_google_security.xml',
        'views/res_config_views.xml',
        'views/res_users_views.xml',
        'views/of_intervention_views.xml',
        'views/of_planning_google_templates.xml',
        'wizards/of_update_rec_rules_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
