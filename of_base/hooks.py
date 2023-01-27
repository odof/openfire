# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.addons.base_iban.models.res_partner_bank import validate_iban
from .models.res_partner import convert_phone_number


def _set_partner_bank_account_type(env):
    for bank in env['res.partner.bank'].search([]):
        try:
            validate_iban(bank.acc_number)
        except ValidationError:
            bank.acc_type = 'bank'


def _set_partner_phones(env, cr):
    partners = env['res.partner'].search([])
    for partner in partners:
        phone_number_ids = []
        cr.execute("SELECT phone, mobile FROM res_partner WHERE id = %s", (partner.id,))
        result = cr.fetchone()
        phone = result[0]
        mobile = result[1]
        country_code = partner.country_id and partner.country_id.code or 'FR'
        if phone:
            number = convert_phone_number(phone, country_code)
            phone_number_ids.append((0, 0, {'number': number, 'type': '01_domicile'}))
        if mobile:
            number = convert_phone_number(mobile, country_code)
            phone_number_ids.append((0, 0, {'number': number, 'type': '03_mobile'}))
        partner.write({'of_phone_number_ids': phone_number_ids})


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _set_partner_bank_account_type(env)
    _set_partner_phones(env, cr)
