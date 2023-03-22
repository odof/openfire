# -*- coding: utf-8 -*-

from odoo import api, fields, models

class OfSaleOrderConfirmation(models.TransientModel):
    _name = 'of.sale.order.confirmation'

    order_id = fields.Many2one('sale.order')

    def button_ok(self):
        action, interrupt = self.env['of.sale.order.verification'].do_verification(self.order_id)
        if interrupt:
            return action
        res = self.order_id.action_confirm()
        if action:
            return action
        return res

    def button_no(self):
        action, interrupt = self.env['of.sale.order.verification'].do_verification(self.order_id)
        if interrupt:
            return action
        res = self.with_context(no_update_confirm=True).order_id.action_confirm()
        if action:
            return action
        return res


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def write(self, vals):
        if self._context.get("no_update_confirm") and self.confirmation_date:
            if 'confirmation_date' in vals:
                del vals['confirmation_date']
        res = super(SaleOrder, self).write(vals)
        return res


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.model
    def _auto_init(self):
        """
        Certain paramètres d'affichage sont passés de Booléen à Sélection.
        Cette fonction est appelée à chaque mise à jour mais ne fait quelque chose que la première fois qu'elle est appelée.
        """
        super(OFSaleConfiguration, self)._auto_init()
        if not self.env['ir.values'].get_default('sale.config.settings', 'of_recalcul_date_confirmation'):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_recalcul_date_confirmation', 1)

    of_recalcul_date_confirmation = fields.Selection(selection=[(1, 'Automatique'), (2, 'Manuel')],
                                                     string="(OF) Recalcul de la date de confirmation")

    @api.multi
    def set_of_recalcul_date_confirmation(self):
        view = self.env.ref('of_sale.of_sale_view_confirmation_date_order_form')
        if view:
            view.write({'active': self.of_recalcul_date_confirmation == 2})
        return self.env['ir.values'].sudo().set_default(
                'sale.config.settings', 'of_recalcul_date_confirmation',
                self.of_recalcul_date_confirmation)
