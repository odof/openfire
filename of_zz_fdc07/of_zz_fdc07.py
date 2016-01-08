# -*- coding: utf-8 -*-

from openerp import models, fields


class res_partner(models.Model):
    
    _inherit = 'res.partner'
    
    of_service = fields.Char(u'Service', size=64)
    
