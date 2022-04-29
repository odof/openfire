# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, models, fields


class OFService(models.Model):
    _inherit = 'of.service'

    type_id = fields.Many2one(domain='[("dispo_service", "=", True)]')


class OFServiceType(models.Model):
    _inherit = 'of.service.type'

    active = fields.Boolean(string=u"Actif", default=True)
    dispo_service = fields.Boolean(string=u"Disponible dans la DI", default=True)
