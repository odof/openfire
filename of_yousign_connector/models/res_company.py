# -*- coding: utf-8 -*-

import uuid

from odoo import api, fields, models, SUPERUSER_ID
from odoo.exceptions import ValidationError


class Company(models.Model):
    _inherit = 'res.company'

    def _auto_init(self):
        self.env['of.yousign.connector.hook']._auto_init_res_company_hook_v16_0_1_0_0()
        res = super(Company, self)._auto_init()
        return res

    of_yousign_external_id = fields.Char(string=u"ID externe (Yousign)", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        res = super(Company, self).create(vals_list)
        for record in res:
            record.of_yousign_external_id = '%s_%i_%s' % (self.env.cr.dbname, record.id, str(uuid.uuid4()))
        return res

    def write(self, vals):
        if 'of_yousign_external_id' in vals and self._uid != SUPERUSER_ID:
            raise ValidationError(u"Seul l'administrateur peut modifier le champ \"ID externe (Yousign)\"")
        res = super(Company, self).write(vals)
        return res
