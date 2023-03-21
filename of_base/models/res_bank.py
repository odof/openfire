# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from schwifty import BIC

from odoo import api, models
from odoo.exceptions import ValidationError


class ResBank(models.Model):
    _inherit = 'res.bank'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('bic'):
                try:
                    BIC(vals['bic'])
                except Exception as e:
                    raise ValidationError("The BIC code is incorrect") from e
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('bic'):
            try:
                BIC(vals['bic'])
            except Exception as e:
                raise ValidationError("The BIC code is incorrect") from e
        return super().write(vals)
