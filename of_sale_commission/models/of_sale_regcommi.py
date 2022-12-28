# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError


class OFSaleRegcommi(models.Model):
    _name = 'of.sale.regcommi'
    _description = u"Règles de commissions"

    name = fields.Char(string=u"Libellé")
    code = fields.Text(string=u"Code")

    _sql_constraints = [
        ('name_id_unique', 'unique (name)', u"Le libellé est déjà utilisé !"),
    ]

    @api.model
    def create(self, vals):
        if self._uid != SUPERUSER_ID:
            raise UserError(u"Seul l'administrateur a le droit de créer des règles !")
        return super(OFSaleRegcommi, self).create(vals)

    @api.multi
    def write(self, vals):
        if self._uid != SUPERUSER_ID:
            raise UserError(u"Seul l'administrateur a le droit de modifier des règles !")
        return super(OFSaleRegcommi, self).write(vals)
