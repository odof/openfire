# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models

from odoo.addons.of_base.models.res_partner import convert_phone_number

_logger = logging.getLogger(__name__)

try:
    import phonenumbers
except ImportError:
    _logger.debug(u"Impossible d'importer la librairie Python 'phonenumbers'.")


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_mobile_numbers(self):
        mobile_numbers = []
        for partner in self:
            for mobile in partner.of_phone_number_ids.filtered(lambda p: p.type == '03_mobile' and p.number):
                phone_number = convert_phone_number(mobile.number, new_format='e164', strict=True)
                if phone_number:
                    mobile_numbers.append(phone_number)
                else:
                    country_code = (
                        (partner.country_id and partner.country_id.code)
                        or (self.env.user.company_id.country_id and self.env.user.company_id.country_id.code)
                        or "FR"
                    )
                    for match in phonenumbers.PhoneNumberMatcher(mobile.number, country_code):
                        phone_number = phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)
                        mobile_numbers.append(phone_number)
        return mobile_numbers
