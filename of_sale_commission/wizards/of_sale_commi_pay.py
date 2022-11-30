# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OFSaleCommiPay(models.TransientModel):
    """
    This wizard will confirm paid all the selected to_pay commis
    """
    _name = 'of.sale.commi.pay'
    _description = "Confirm paid the selected to_pay commis"

    @api.model
    def _default_draft(self):
        return self._check_state(('draft', ))

    @api.model
    def _default_cancel(self):
        return self._check_state(('cancel', ))

    @api.model
    def _default_paid(self):
        return self._check_state(('paid', ))

    draft = fields.Boolean(default=lambda self: self._default_draft())
    cancel = fields.Boolean(default=lambda self: self._default_cancel())
    paid = fields.Boolean(default=lambda self: self._default_paid())
    date = fields.Date(string="Date de paiement", required=True, default=fields.Date.today)

    @api.model
    def _check_state(self, states):
        commis = self.env['of.sale.commi'].browse(self._context.get('active_ids', []))
        return commis.filtered(lambda commi: commi.state in states)

    @api.multi
    def confirmer_paiement(self):
        commis = self.env['of.sale.commi']\
            .browse(self._context.get('active_ids', []))\
            .filtered(lambda c: c.state in ('draft', 'to_pay'))
        dated_commis = commis.filtered('date_valid')
        order_commis_not_paid = commis.mapped('order_commi_ids').filtered(lambda c: c.state != 'paid')
        order_commis_not_paid = order_commis_not_paid - commis
        if order_commis_not_paid:
            raise UserError(_(
                u"Pour valider des commissions sur solde, vous devez également valider les commissions sur acompte "
                u"associées dont le paiement n'a pas encore été confirmé"))
        if dated_commis:
            dated_commis.write({'state': 'paid', 'date_paiement': self.date})
        if len(dated_commis) != len(commis):
            (commis - dated_commis).write({'state': 'paid', 'date_paiement': self.date, 'date_valid': self.date})
