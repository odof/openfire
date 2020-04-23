# -*- coding: utf-8 -*-

from odoo import api, fields, models


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    active = fields.Boolean(string="Actif", default=True)


class UtmMedium(models.Model):
    _inherit = 'utm.medium'

    source_ids = fields.One2many('utm.source', 'medium_id', string="Origines disponibles")


class UtmSource(models.Model):
    _inherit = 'utm.source'
    _order = 'sequence'

    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    medium_id = fields.Many2one('utm.medium', string='Canal associé')


class UtmMixin(models.AbstractModel):
    _inherit = 'utm.mixin'

    source_id = fields.Many2one(domain="[('medium_id', '=', medium_id)]")

    @api.onchange('medium_id')
    def _onchange_medium_id(self):
        if self.medium_id:
            self.source_id = self.medium_id.source_ids and self.medium_id.source_ids[0] or False
        else:
            self.source_id = False
