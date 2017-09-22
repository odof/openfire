# -*- coding: utf-8 -*-

{
    'name' : "OpenFire Base MultiSociété",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'complexity': "easy",
    'description' : """
Personnalisation de la multi-société :

- Les champs company-dependent se lisent au niveau de la société comptable au lieu de la société courante.
- Modification des droits pour permettre l'utilisation de la configuration comptable des sociétés parentes.
- Lasociété des comptes comptables est forcée au niveau d'une société comptable.
""",
    'website' : "www.openfire.fr",
    'depends' : ['account'],
    'category' : "OpenFire",
    'data' : [
        'security/of_base_multicompany_security.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
