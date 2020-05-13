# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Calendrier",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'category': 'OpenFire modules',
    'summary': 'Calendar custom colors',
    'license': 'AGPL-3',
    "description": """
Module OpenFire des calendriers
===============================

- Ajout des champs 'of_color_ft' et 'of_color_bg' dans res.users et res.partner
- Ajout choix des couleurs dans les calendriers
- Ajout configuration du drag and drop dans les paramètres système (Configuration -> Technique -> Paramètres)
- Ajout de la possibilité d'afficher une vue calendar d'un champ One2many

Vue calendar
------------

- attribut 'custom_colors': mettre à "1" pour utiliser les couleurs custom
- attribut 'attendee_model': nom du modèle des participants, inutile si 'use_contacts' à "1". exemple: attendee_model="res.partner"
- attribut 'color_bg_field' et 'color_ft_field': nom des champs de couleur de texte et de fond
- attribut 'filters_radio': mettre à "1" pour que les filtres de la barre latérale soient de type radio button
- attribut 'jump_to': mettre à "first", "last" ou "selected"
- attribut 'dispo_field': champ de disponibilité utilisé si 'show_first_evt' est à "1"
- attribut 'force_color_field': champ utilisé pour forcer la couleur d'un évenement
- attribut 'color_multiple': mettre à "1" si on veut pouvoir coloriser les evts de différentes manières
- si 'use_contacts' à "1": 'color_bg_field' est à 'of_color_bg' (le champ de res.partner)
- si 'use_contacts' à "0": 'color_bg_field' est le nom du champs couleur de l'objet du calendrier. exemple 'of_color_bg' pour "calendar.event"
- ajout gestion de l'attribut invisible="1" dans les fields de la vue calendar

Etat des évènements d'un calendrier (classe abstraite 'of.calendar.mixin')
--------------------------------------------------------------------------

Les objets implémentant une vue calendrier et des états peuvent desormais hériter de 'of.calendar.mixin'.
Leur classe devra définir les fonctions '_compute_state_int' et 'get_state_int_map'.
Leur balise calendar devra contenir l'attribut display_states="1".

Employés
--------

- ajout de champs couleurs
- ajout de la gestion des horaires
""",
    "website": "www.openfire.fr",
    "depends": [
        "hr",
        "web_widget_color",
        "calendar",
        "web_calendar",
        "of_web_widgets",
        "of_geolocalize",
        "of_utils",
    ],
    "data": [
        "data/ir_config_parameter_data.xml",
        "data/of_calendar_data.xml",
        "views/of_web_calendar_templates.xml",
        "wizards/of_horaire_wizard_view.xml",
        "views/of_calendar_views.xml",
        "security/ir.model.access.csv",
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
