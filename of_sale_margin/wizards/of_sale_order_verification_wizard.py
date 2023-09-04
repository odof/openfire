# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class OfSaleOrderVerification(models.TransientModel):
    _inherit = 'of.sale.order.verification'

    type = fields.Selection(selection_add=[('margin', "Margin")])

    @api.model
    def do_verification(self, order):
        action, need_interruption = super(OfSaleOrderVerification, self).do_verification(order)
        if self.env['ir.config_parameter'].sudo().get_param('of.sale.margin.of_sale_order_margin_control'):
            # Check margin on main product category
            sale_responsible = self.env.user.has_group('sales_team.group_sale_manager')
            context = self._context.copy()
            skipped_types = context.get('skipped_types', [])
            if 'margin' not in skipped_types and not context.get('no_verif_margin', False):
                # we are assuming that there is only one main product per order, so we take the first one
                of_main_product = order.order_line.filtered('of_main_product')
                of_main_product = of_main_product and of_main_product[0].product_id or False
                if (
                    of_main_product
                    and of_main_product.categ_id.of_margin_rate
                    and int(order.of_margin_percent) < of_main_product.categ_id.of_margin_rate
                ):
                    action_str = sale_responsible and _("request") or _("requires")
                    message = _(
                        "The margin amount of the order \"%s\" is %.2f%% while the "
                        "category \"%s\" of the main product \"%s\" %s a minimum margin of %s%%."
                    ) % (
                        order.name,
                        order.of_margin_percent,
                        of_main_product.categ_id.name,
                        of_main_product.display_name,
                        action_str,
                        of_main_product.categ_id.of_margin_rate,
                    )
                    skipped_types.append('margin')
                    context.update(
                        {
                            'default_type': 'margin',
                            'default_message': message,
                            'default_order_id': order.id,
                            'skipped_types': skipped_types,
                        }
                    )
                    return self.with_context(context).action_open_wizard(), self.need_interruption(order)
        return action, need_interruption

    @api.model
    def need_interruption(self, order=False):
        sale_responsible = self.env.user.has_group('sales_team.group_sale_manager')
        context = self._context.copy()
        skipped_types = context.get('skipped_types', [])
        if 'margin' not in skipped_types and not context.get('no_verif_margin', False) and not sale_responsible:
            of_main_product = order.order_line.filtered('of_main_product')
            of_main_product = of_main_product and of_main_product[0].product_id or False
            if (
                of_main_product
                and of_main_product.categ_id.of_margin_rate
                and int(order.of_margin_percent) < of_main_product.categ_id.of_margin_rate
            ):
                return True
        return False
