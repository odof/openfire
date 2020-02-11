# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_archive_count = fields.Integer(string="Archives", compute='_compute_of_archive_count')

    @api.multi
    def _compute_of_archive_count(self):
        for partner in self:
            partner.of_archive_count = self.env['of.archive'].search_count([('partner_id', '=', partner.id)])
