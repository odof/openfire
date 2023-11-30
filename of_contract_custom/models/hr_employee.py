# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    of_is_provider = fields.Boolean(string=u"Est prestataire")
    of_provider_id = fields.Many2one(
        comodel_name='res.partner', string=u"Prestataire", domain="[('supplier','=',True)]")

    @api.onchange('of_is_provider')
    def _onchange_of_provider_id(self):
        if not self.of_is_provider:
            self.of_provider_id = False

    @api.onchange('of_est_intervenant', 'of_est_commercial')
    def _onchange_est_intervenant(self):
        res = super(HREmployee, self)._onchange_est_intervenant()
        if not self.of_est_intervenant and not self.of_est_commercial:
            self.of_is_provider = False
            self.of_provider_id = False
        return res
