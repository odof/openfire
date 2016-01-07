# -*- coding: utf-8 -*-


from openerp import models, fields
import time


class of_liste_docs(models.Model):
    _name = "of.liste.docs"
    _description = "Liste documents"
    
    name = fields.Char(u'Nom', size=64)
    date = fields.Date(u'Date document')
    categorie = fields.Many2one('of.liste.docs.categorie', u'Catégorie', required=False, ondelete='restrict')
    file = fields.Binary(u'Fichier')
    file_name = fields.Char(u'Nom du fichier', size=64)
    
    _rec_name = 'name'
    
    _defaults = {
        'date': time.strftime('%Y-%m-%d'),
    }


class of_liste_docs_categorie(models.Model):
    _name = "of.liste.docs.categorie"
    
    name = fields.Char(u'Catégorie', size=32)

