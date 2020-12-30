# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
{
    "name": "Mass Label Reporting",
    "version": "10.0.1.0.0",
    "author": 'Serpent Consulting Services Pvt. Ltd. / modified by OpenFire SAS',
    'maintainer': 'OpenFire SAS',
    "category": "Tools",
    "license": "AGPL-3",
    "website": "http://www.serpentcs.com",
    "summary": "Generate customised labels of any document",
    "description": """
    Seul le compte admin peut accéder à la configuration des étiquettes. Configuration > Technique > Impression d'étiquettes
    
    Label Configuration: les différents patrons d'étiquettes (exemple OpenFire - 2 x 2 paysage)
    
    Label Print: les différents contenus d'étiquettes (exemple Étiquette de stock 2x2)
    
    Une fois le module installé vous pouvez créer des actions contextuelles pour vos impression d'étiquettes.
    Pour ce faire, dans l'étiquettes que vous voulez utiliser > Onglet Advance > cliquer sur "Add sidebar button".
    Vous pouvez ensuite imprimer des étiquettes dans l'objet concerné depuis le bouton d'actions
    
    Exemple: Après avoir installé ce module, je veux utiliser les étiquettes de stock fournies par défaut.
    Je vais dans Configuration > Technique > Impression d'étiquettes > Label Print et je choisis "étiquette de stock 2x2".
    Je clique sur le bouton "Add sidebar button" dans l'onglet "Advance".
    Je peux désormais aller dans un BL ou BR et cliquer sur Action > Label (étiquette de stock 2x2).
    Je choisis le nombre de copies de chaques lignes et les lignes à imprimer et clique sur "PRINT".
    Et voilà! j'ai un PDF avec mes étiquettes de stock!
    
    The video : https://www.youtube.com/watch?v=Fps5FWfcLwo
    """,
    'depends': [
        'of_base',
        'report',
    ],
    'data': [
        'report/label_template_views.xml',
        'data/label_config_data.xml',
        'data/label_print_data.xml',
        # /!\ l'ordre de déclaration des 3 fichiers précédents est à conserver.
        'data/report_paperformat.xml',
        'report/dynamic_label.xml',
        'security/ir.model.access.csv',
        'views/label_config_view.xml',
        'views/label_print_view.xml',
        'views/label_report.xml',
        'wizard/label_print_wizard_view.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'images': ['static/description/Label.png'],
    'installable': True,
    'auto_install': False,
}
