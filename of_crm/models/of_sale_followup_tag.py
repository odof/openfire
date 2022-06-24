# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import random
from odoo import models, fields, api


class OFSaleFollowupTag(models.Model):
    _name = 'of.sale.followup.tag'
    _description = "Order tracking label"

    @api.model_cr_context
    def _auto_init(self):
        res = super(OFSaleFollowupTag, self)._auto_init()
        ir_config_obj = self.env['ir.config_parameter']
        existing_tags = self.search([])
        if not ir_config_obj.get_param('of.sale.followup.tag.data.loaded') and not existing_tags:
            for name in ['Appro OK', 'Admin OK', 'Planif OK']:
                self.create({'name': name, 'color': random.randint(0, 10)})
        if not ir_config_obj.get_param('of.sale.followup.tag.data.loaded'):
            ir_config_obj.set_param('of.sale.followup.tag.data.loaded', 'True')
        return res

    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'This tag name already exists !'),
    ]
