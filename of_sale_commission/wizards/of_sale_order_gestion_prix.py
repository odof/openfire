# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class GestionPrix(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix'

    @api.multi
    def calculer(self, simuler=False):
        super(GestionPrix, self).calculer(simuler=simuler)
        if not simuler:
            self.order_id.of_commi_ids.filtered(
                lambda commi: (commi.total_du >= 0 and
                               commi.state not in ('paid', 'to_cancel', 'cancel', 'paid_cancel'))
            ).update_commi()
