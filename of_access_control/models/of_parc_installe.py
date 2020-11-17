# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFParcInstalle(models.Model):
    _inherit = 'of.parc.installe'

    company_id = fields.Many2one(comodel_name='res.company', string=u"Société")

    @api.onchange('client_id')
    def _onchange_client_id(self):
        super(OFParcInstalle, self)._onchange_client_id()
        if self.client_id:
            self.company_id = self.client_id.company_id
