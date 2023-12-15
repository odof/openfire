# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OfPlanningMessageInvoice(models.TransientModel):
    _name = 'of.planning.message.invoice'
    _description = u'Création de la facture'

    @api.model
    def _default_name(self):
        return self._context.get('default_msg', '')

    name = fields.Text(string="Note", default=_default_name)
