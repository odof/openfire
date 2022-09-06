# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_is_telecom = fields.Boolean(string=u"Article Télécom")
    of_telecom_type = fields.Selection(
        selection=[('telephony', u"Telephony"), ('internet', u"Internet")], string=u"Type de Télécom")
    of_optical_fiber_type = fields.Selection(
        selection=[('ffth', u"FFTH (fiber to the home)"), ('ffto', u"FFTO (fiber to the office)")],
        string=u"Type de Fibre")

    @api.onchange('of_is_telecom')
    def _onchange_of_is_telecom(self):
        if self.of_is_telecom:
            self.of_telecom_type = 'telephony'
        else:
            self.of_telecom_type = False

    @api.onchange('of_telecom_type')
    def _onchange_of_telecom_type(self):
        if self.of_telecom_type == 'internet':
            self.of_optical_fiber_type = 'ffth'
        else:
            self.of_optical_fiber_type = False
