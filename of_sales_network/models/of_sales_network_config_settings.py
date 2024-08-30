# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSalesNetworkConfigSettings(models.TransientModel):
    _name = 'of.sales.network.config.settings'
    _inherit = 'res.config.settings'
    _description = u"Configuration du Réseau Commercial"

    company_id = fields.Many2one(
        comodel_name='res.company', string=u"Société", required=True, default=lambda self: self.env.user.company_id)
