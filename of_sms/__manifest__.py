# -*- coding: utf-8 -*-
{
    'name' : "OpenFire / SMS",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'license': 'LGPL-3',
    'website' : "www.openfire.fr",
    'category' : "Generic Modules/",
    'description': u"""
Module de SMS OpenFire
======================

- Gestion de la passerelle OVH
- Envoi de SMS depuis les partenaires, les prospects/opportunités, le planning d'intervention instantanément ou en différé
- Modèles de SMS
- Tâche automatique journalière envoyant des textos de rappel la veille aux équipes d'intervention et/ou aux clients
""",
    'depends' : [
        'mail',
        'of_planning_tournee',
        'of_crm',
    ],
    'demo_xml' : [],
    'data': [
        'security/ir.model.access.csv',
        'data/of_sanitize_query.xml',
        'data/of_sms_data.xml',
        'views/of_sms_views.xml',
        'wizard/of_sms_compose_views.xml',
    ],
    'installable': True,
}
