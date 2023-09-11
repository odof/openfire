# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_account_id = fields.Many2one(
        comodel_name='account.analytic.account', string=u"Compte analytique par défaut",
        domain="[('company_id', '=', id)]", required=True)
