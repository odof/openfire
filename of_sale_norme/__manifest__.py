# -*- coding: utf-8 -*-

{
    "name": "OpenFire Normes",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'category': 'OpenFire modules',
    'summary': 'Normes',
    'license': 'AGPL-3',
    "description": """
Normes des produits vendus OpenFire
====================================

- Création de l'objet 'Norme' et des vues associées
- Ajout des champs 'norme_id' et 'description_norme' dans les articles
- Report du champ 'description_norme' dans les lignes de devis et de factures si elle est active et que la case 'Afficher en impression' est cochée

Objet Norme
-----------

Cet objet contient 4 champs:

- Code (name): le code de la norme
- Libellé (libelle): une brève description de la norme
- Description (description): une description détaillée de la norme
- Afficher en impression (display_docs): cocher cette case pour ajouter la description de la norme dans les devis et factures

Il est possible d'archiver une norme.

La description d'une norme est copiée dans l'article quand elle lui est associée. Elle peut ensuite être modifiée article par article.
""",
    "website": "www.openfire.fr",
    "depends": ["sale"],
    "category": "OpenFire",
    "data": [
        'views/of_sale_norme_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
