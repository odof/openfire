# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFSaleOrderAddQuoteWizard(models.TransientModel):
    _inherit = 'of.sale.order.add.quote.wizard'

    @api.multi
    def add_quote(self):
        super(OFSaleOrderAddQuoteWizard, self).add_quote()
        order = self.order_id
        active_commis = order.of_commi_ids.filtered(
            lambda c: c.total_du >= 0 and c.state != 'paid' and not c.cancel_commi_id)
        active_commis.update_commi()
        order.of_verif_acomptes()
