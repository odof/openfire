# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(selection=[
        ('draft', u"Estimation"),
        ('sent', u"Devis"),
        ('presale', u"Bon de commande"),
        ('sale', u"Commande enregistrée"),
        ('done', u"Verrouillé"),
        ('cancel', u"Annulé"),
        ('closed', u"Clôturé"),
    ])
    of_custom_confirmation_date = fields.Datetime(string=u"Date de confirmation")
    confirmation_date = fields.Datetime(string=u"Date d'enregistrement")

    @api.multi
    def action_preconfirm(self):
        for order in self:
            order.state = 'presale'
            order.of_custom_confirmation_date = fields.Datetime.now()
            if not self._context.get('order_cancellation', False):
                order.with_context(auto_followup=True, followup_creator_id=self.env.user.id).sudo().\
                    action_followup_project()
        return True

    @api.multi
    def action_reopen(self):
        self.ensure_one()
        # On ré-ouvre le suivi
        if self.of_followup_project_id:
            self.of_followup_project_id.set_to_in_progress()
        self.state = 'sale'
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    confirmation_date_order = fields.Datetime(string=u"Date d'enregistrement de commande")
    of_confirmation_date = fields.Datetime(string=u"Date d'enregistrement")


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_recalcul_date_confirmation = fields.Selection(string=u"(OF) Recalcul de la date d'enregistrement")
