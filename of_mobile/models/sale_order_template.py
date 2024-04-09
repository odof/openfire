# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    of_mobile_available = fields.Boolean(string="Mobile Product")
    of_mobile_can_create_additional_sale = fields.Boolean(compute='_compute_of_mobile_can_create_additional_sale')

    def _compute_of_mobile_can_create_additional_sale(self):
        for sot in self:
            sot.of_mobile_can_create_additional_sale = self.env.company.of_mobile_can_create_additional_sale

    def action_button_toggle_mobile(self):
        self.ensure_one()

        if not self.of_mobile_available:
            if not self.of_payment_term_id and not self.of_fiscal_position_id:
                raise UserError(_("You must add a Payment Term and a Fiscal Position to publish this template"))
            elif not self.of_fiscal_position_id:
                raise UserError(_("You must add a fiscal position to publish this template"))
            elif not self.of_payment_term_id:
                raise UserError(_("You must add a payment term to publish this template"))

        self.of_mobile_available = not self.of_mobile_available
        if self.of_mobile_available:
            # alors on doit aussi publier les articles du devis s'ils ne le sont pas
            for product in self.sale_order_template_line_ids.mapped('product_id'):
                if not product.of_mobile_available:
                    product.product_tmpl_id.action_button_toggle_mobile()

    @api.model
    def _prepare_graphql_domain(self, select, domain):
        odoo_domain = super()._prepare_graphql_domain(select, domain)

        if select and 'mobile' in select:
            odoo_domain += [('of_mobile_available', '=', select.mobile)]

        return odoo_domain
