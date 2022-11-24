# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    of_profcommi_id = fields.Many2one('of.sale.profcommi', string="Profil Commissions", ondelete='restrict')
