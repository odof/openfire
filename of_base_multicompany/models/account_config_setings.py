# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    accounting_company_id = fields.Many2one(
        comodel_name='res.company', related='company_id.accounting_company_id', string=u"Société comptable",
        readonly=True
    )
