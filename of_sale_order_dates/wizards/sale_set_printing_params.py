# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api


class OFSaleWizardSetPrintingParams(models.TransientModel):
    _inherit = 'of.sale.wizard.set.printing.params'

    of_pdf_display_requested_week = fields.Boolean(
        string=u"(OF) Afficher pastille 'Semaine demandée'", required=True, default=False,
        help=u"Afficher la pastille 'Semaine demandée' dans les rapports PDF ?")

    @api.multi
    def set_of_pdf_display_requested_week(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_pdf_display_requested_week', self.of_pdf_display_requested_week)
