# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    of_default_tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="account_fiscal_position_account_tax_rel",
        column1="account_fiscal_position_id",
        column2="account_tax_id",
        string="Default taxes",
        help="Taxes used when no tax account is defined in the article",
    )

    def map_tax(self, taxes):
        if not self:
            if self._context.get("website_id"):
                return taxes
            raise UserError(_("Please enter a tax position"))  # Veuillez renseigner une position fiscale
        self.ensure_one()
        if not taxes:
            taxes = self.of_default_tax_ids
        return super().map_tax(taxes)

    @api.model
    def _get_fpos_by_region(self, country_id=False, state_id=False, zipcode=False, vat_required=False):
        """In case a customer has no country, we want to get a default fiscal position anyway"""
        if country_id:
            return super()._get_fpos_by_region(
                country_id=country_id, state_id=state_id, zipcode=zipcode, vat_required=vat_required
            )

        base_domain = [
            ("auto_apply", "=", True),
            ("vat_required", "=", vat_required),
            ("company_id", "in", [self.env.company.id, False]),
        ]
        null_country_dom = [("country_id", "=", False), ("country_group_id", "=", False)]

        fpos = self.search(base_domain + null_country_dom, limit=1)
        return fpos or False
