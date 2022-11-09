# -*- encoding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    'name': u"OpenFire / RDVs réguliers",
    'version': '10.0.1.0.0',
    'author': u"OpenFire",
    'website': 'http://www.openfire.fr',
    'category': u"Generic Modules/Gestion des interventions",
    'license': u"AGPL-3",
    'description': u"""Gestion des RDVs réguliers
     - Possibilité de créer des RDVs réguliers dans le planning d'interventions
     
     la fonctionnalité s'active dans la configuration des interventions.""",
    'depends': [
        'of_questionnaire',
        'of_planning_tournee'
    ],
    'init_xml': [],
    'demo_xml': [],
    'data': [
        'data/of_planning_recurring_data.xml',
        'security/of_planning_recurring_security.xml',
        'views/of_intervention_views.xml',
        'views/of_planning_recurring_templates.xml',
        'views/of_planning_recurring_views.xml',
        'wizards/of_update_rec_rules_wizard_views.xml',
    ],
    'installable': True,
}
