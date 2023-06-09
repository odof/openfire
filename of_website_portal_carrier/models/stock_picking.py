# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, api, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_validated_by_carrier = fields.Boolean(string=u"Validé par le transporteur", copy=False)
    of_carrier_validation_date = fields.Datetime(string=u"Validé par le transporteur le", copy=False)
    of_need_backorder = fields.Boolean(string=u"Créer le reliquat", copy=False)
    of_error_message = fields.Text(string=u"Message d'erreur", copy=False)

    @api.model
    def validate_picking_from_carriers(self):
        backorder_confirmation_obj = self.env['stock.backorder.confirmation']
        delay = self.env['ir.values'].sudo().get_default('website.config.settings', 'of_picking_rollback_delay')
        time_for_domain = fields.Datetime.to_string(datetime.now() - relativedelta(minutes=delay))
        domain = [('state', 'not in',['done', 'cancel']), ('of_carrier_validation_date', '<=', time_for_domain)]
        pickings_done = self
        pickings_to_validate = self.search(domain)
        for picking in pickings_to_validate:
            # catching exceptions just in case
            try:
                action = picking.do_new_transfer()
                if action and action.get('res_id'):
                    wizard = backorder_confirmation_obj.browse(action['res_id'])
                    if picking.of_need_backorder:
                        wizard.process()
                    else:
                        wizard.process_cancel_backorder()
                pickings_done += picking
            except Exception as e:
                continue
        if pickings_done:
            pickings_done.write({'of_validated_by_carrier': True})

    @api.multi
    def write(self, vals):
        # Vider le message d'erreur si il y en a un
        if 'of_error_message' not in vals and self.mapped('of_error_message'):
            vals['of_error_message'] = False
        return super(StockPicking, self).write(vals)
