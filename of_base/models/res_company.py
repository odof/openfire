# -*- coding: utf-8 -*-

from odoo import models, api, SUPERUSER_ID
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        if self._uid != SUPERUSER_ID:
            raise ValidationError(u"Seul l'administrateur peut créer une nouvelle société.")
        return super(ResCompany, self).create(vals)

    @api.multi
    def unlink(self):
        if self._uid != SUPERUSER_ID:
            raise ValidationError(u"Seul l'administrateur peut supprimer une société.")
        return super(ResCompany, self).unlink()

    @api.model
    def get_allowed_company_ids(self):
        return self.env.user.company_ids.ids
