# -*- coding: utf-8 -*-

from openerp import models, fields, api


# Catégories de partenaires
class of_partner_categ(models.Model):
    
    _name = "of.partner.categ"
    
    name = fields.Char(u'Catégorie', size=32)
    parent_id = fields.Many2one('of.partner.categ', 'Catégorie parente', select=True, ondelete='restrict')
    
    _constraints = [
        (models.Model._check_recursion, 'Error ! You can not create recursive category.', ['parent_id'])
    ]

    # Pour afficher la hiérarchie des catégories
    @api.multi
    def name_get(self):
        if not self._ids:
            return []
        res = []
        for record in self:
            name = [record.name]
            parent = record.parent_id
            while parent:
                name.append(parent.name)
                parent = parent.parent_id
            name = ' / '.join(name[::-1])
            res.append((record.id, name))
        return res



class res_partner(models.Model):
    
    _inherit = 'res.partner'
    
    of_categ_id = fields.Many2one('of.partner.categ', u'Catégorie', required=False, ondelete='restrict')