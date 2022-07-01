# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.exceptions import ValidationError
from schwifty import BIC


class ResBank(models.Model):
    _inherit = 'res.bank'

    @api.model
    def create(self, vals):
        if vals.get('bic'):
            try:
                BIC(vals['bic'])
            except Exception as e:
                raise ValidationError("Le code bic est incorrect")
        return super(ResBank, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('bic'):
            try:
                BIC(vals['bic'])
            except Exception as e:
                raise ValidationError("Le code bic est incorrect")
        return super(ResBank, self).write(vals)
