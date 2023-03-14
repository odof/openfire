# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    of_online_booking = fields.Boolean(name=u"RDV en ligne", default=True)

