# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Calendrier",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'category': 'OpenFire modules',
    'summary': 'Calendar custom colors',
    'license': 'AGPL-3',
    "description": """
Module OpenFire des calendrier
==============================

- Ajout des champs 'of_color_ft' et 'of_color_bg' dans res.users et res.partner
- Ajout choix des couleurs dans les calendriers
- Ajout configuration du drag and drop dans les paramètres systèmes (configuration -> technique -> paramètres)

Vue calendar
------------

- attribut 'custom_colors': mettre à "1" pour utiliser les couleurs custom
- attribut 'attendee_model': nom du modèle des participants, inutile si 'use_contacts' à "1". exemple: attendee_model="res.partner"
- attribut 'color_bg_field' et 'color_ft_field': nom des champs de couleur de texte et de fond
- si 'use_contacts' à "1": 'color_bg_field' est à 'of_color_bg' (le champ de res.partner)
- si 'use_contacts' à "0": 'color_bg_field' est le nom du champs couleur de l'objet du calendrier. exemple 'of_color_bg' pour "calendar.event"
- ajout gestion de l'attribut invisible="1" dans les fields de la vue calendar

Etat des évènements d'un calendrier (classe abstraite 'of.calendar.mixin')
--------------------------------------------------------------------------

Les objets implémentant une vue calendrier et des états peuvent desormais hériter de 'of.calendar.mixin'.
Leur classe devra définir les fonctions '_compute_state_int' et 'get_state_int_map'.
Leur balise calendar devra contenir l'attribut display_states="1".
""",
    "website": "www.openfire.fr",
    "depends": [
        "web_widget_color",
        "calendar",
        "web_calendar",
    ],
    "data": [
        "data/ir_config_parameter_data.xml",
        "views/of_web_calendar_templates.xml",
        "views/of_calendar_views.xml",
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
