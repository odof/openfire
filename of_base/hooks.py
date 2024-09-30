# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, Command, api
from odoo.exceptions import ValidationError

from odoo.addons.base_iban.models.res_partner_bank import validate_iban

from .models.res_partner import convert_phone_number


def _set_partner_bank_account_type(env):
    for bank in env["res.partner.bank"].search([]):
        try:
            validate_iban(bank.acc_number)
        except ValidationError:
            bank.acc_type = "bank"


def _set_partner_phones(env, cr):
    cr.execute("SELECT id, phone, mobile FROM res_partner")
    partner_phones = {}
    for partner_id, phone, mobile in cr.fetchall():
        vals = {}
        if phone:
            vals["01_domicile"] = phone
        if mobile:
            vals["03_mobile"] = mobile
        if vals:
            partner_phones[partner_id] = vals

    for partner in env["res.partner"].browse(partner_phones):
        country_code = partner.country_id.code or "FR"
        phone_number_ids = []
        for phone_type, phone_number in partner_phones[partner.id].items():
            if number := convert_phone_number(phone_number, country_code):
                phone_number_ids.append(Command.create({"number": number, "type": phone_type}))
        if phone_number_ids:
            partner.write({"of_phone_number_ids": phone_number_ids})


def post_init_hook(cr, registry):
    """Migrate data from old fields to new ones."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    # data migration
    _set_partner_bank_account_type(env)
    _set_partner_phones(env, cr)


def pre_init_hook(cr):
    """Deactivate the search view of the sms module causing the problem and we re-enable it in `of_base_sms`.
    That view is in conflict with our search view, so we deactivate it to resolve the conflict in a specific
    auto-installed module depending on `sms` and `of_base`."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    if env["ir.module.module"]._get("sms").state == "installed":
        env.ref("sms.res_partner_view_search").active = False
