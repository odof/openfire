# -*- coding: utf-8 -*-
{
    'name' : "OpenFire / SMS",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'license': 'LGPL-3',
    'website' : "www.openfire.fr",
    'category' : "Generic Modules/",
    'description': u"""
Module de SMS OpenFire.
=======================

- Gestion de la passerelle OVH
- Envoi de SMS à la demande depuis les partenaires, instantanément ou en différé
- Modèles de SMS
- CRON journalier envoyant des SMS de rappel la veille aux équipes d'intervention et/ou aux clients d'interventions
""",
    'depends' : [
        'mail',
        'of_calendar',
        'of_planning_tournee',
    ],
    'demo_xml' : [],
    'data': [
        'data/ir.cron.csv',
        'data/mail.message.subtype.csv',
        'data/of.sms.gateway.csv',
        'data/of.sms.gateway.ovh.csv',
        'data/of.sms.template.csv',
        'data/calendar.alarm.csv',
        "views/of_sms_management_views.xml",
        "views/of_sms_message_views.xml",
        "views/of_sms_ir_res_views.xml",
        "views/of_sms_alarm_views.xml",
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
