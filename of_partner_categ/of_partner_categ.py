# -*- coding: utf-8 -*-

from openerp import models, fields


# Catégories de partenaires
class of_partner_categ(models.Model):
    
    _name = "of.partner.categ"
    
    name = fields.Char(u'Catégorie', size=32)
    parent_id = fields.Many2one('of.partner.categ', 'Catégorie parente', select=True, ondelete='restrict')
    
    _constraints = [
        (models.Model._check_recursion, 'Error ! You can not create recursive category.', ['parent_id'])
    ]


class res_partner(models.Model):
    
    _inherit = 'res.partner'
    
    of_categ_id = fields.Many2one('of.partner.categ', u'Catégorie', required=False, ondelete='restrict')