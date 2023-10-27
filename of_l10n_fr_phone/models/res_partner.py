# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields
from odoo.addons.of_base.models.partner import convert_phone_number


class ResPartner(models.Model):
    _inherit = 'res.partner'

    phone = fields.Char(store=True)
    mobile = fields.Char(store=True)
    fax = fields.Char(store=True)

    @api.depends('of_phone_number_ids', 'of_phone_number_ids.type', 'of_phone_number_ids.number')
    def _compute_old_phone_fields(self):
        for rec in self:
            phone = rec.of_phone_number_ids.filtered(lambda p: p.type == '01_domicile')
            if not phone:
                phone = rec.of_phone_number_ids.filtered(lambda p: p.type == '02_bureau')
            if phone:
                rec.phone = convert_phone_number(phone[0].number, 'FR', new_format='country')
            mobile = rec.of_phone_number_ids.filtered(lambda p: p.type == '03_mobile')
            if mobile:
                rec.mobile = convert_phone_number(mobile[0].number, 'FR', new_format='country')
            fax = rec.of_phone_number_ids.filtered(lambda p: p.type == '04_fax')
            if fax:
                rec.fax = convert_phone_number(fax[0].number, 'FR', new_format='country')
