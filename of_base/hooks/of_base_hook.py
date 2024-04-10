# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models
from ..models.partner import convert_phone_number


class OFBaseHook(models.AbstractModel):
    _name = 'of.base.hook'

    @api.model
    def _init_partner_phone(self):
        """
        Recover old phone numbers
        """
        cr = self._cr
        cr.execute("SELECT id, phone, mobile, fax FROM res_partner")
        partner_phone = {}
        for partner_id, phone, mobile, fax in cr.fetchall():
            vals = {}
            if phone:
                vals['01_domicile'] = phone
            if mobile:
                vals['03_mobile'] = mobile
            if fax:
                vals['04_fax'] = fax
            if vals:
                partner_phone[partner_id] = vals
        for partner in self.env['res.partner'].with_context(mail_notrack=True).browse(partner_phone):
            country_code = partner.country_id.code or "FR"
            phone_number_ids = []
            for code, number in partner_phone[partner.id].iteritems():
                number = convert_phone_number(number, country_code)
                if number:
                    phone_number_ids.append((0, 0, {'number': number, 'type': code}))
            if phone_number_ids:
                partner.write({'of_phone_number_ids': phone_number_ids})

    @api.model
    def _update_version_10_0_1_2_0_hook(self):
        module_self = self.env['ir.module.module'].search(
            [('name', '=', 'of_base'), ('state', 'in', ['installed', 'to upgrade'])])
        actions_todo = module_self and module_self.latest_version and module_self.latest_version < '10.0.1.2.0'
        if actions_todo:
            rule = self.env.ref('of_base.of_base_res_partner_rule', raise_if_not_found=False)
            if rule:
                rule.write(
                    {'domain_force': "['|', '|', ('company_id', 'child_of', user.company_ids.ids), "
                        "('company_id', '=', False), ('supplier', '=', True)]"})
