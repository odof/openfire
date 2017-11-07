# -*- coding: utf-8 -*-

{
    'name' : "OpenFire Base MultiSociété",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'complexity': "easy",
    # Réduction de la séquence pour permettre un chargement avant celui des autres modules (à réduire encore au besoin)
    'sequence': 40,
    'description' : """
Personnalisation de la multi-société :

- Les champs company-dependent se lisent au niveau de la société comptable au lieu de la société courante.
- Modification des droits pour permettre l'utilisation de la configuration comptable des sociétés parentes.
- La société des comptes comptables est forcée au niveau d'une société comptable.
- Modification des droits pour permettre la manipulation d'éléments comptables de la société comptable.
""",
    'website' : "www.openfire.fr",
    'depends' : ['account'],
    'category' : "OpenFire",
    'data' : [
        'security/of_base_multicompany_security.xml',
        'views/account_invoice_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
