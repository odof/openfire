# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosConfigSettings(models.TransientModel):
    _inherit = 'pos.config.settings'

    default_invoice_customer_id = fields.Many2one('res.partner', string=u"Client facture par défaut")

    @api.multi
    def set_default_default_invoice_customer_id(self):
        self.env['ir.values'].sudo().set_default(
            'pos.config.settings', 'default_invoice_customer_id',
            self.default_invoice_customer_id.id)
