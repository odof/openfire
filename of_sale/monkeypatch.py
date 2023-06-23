# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools import float_compare

from odoo.addons.sale.models.sale_order_line import SaleOrderLine
from odoo.addons.sale.wizard.mail_compose_message import MailComposeMessage

# We are 🐒-patching the following methods :
#    - sale.order.line._compute_price_unit()
#    - sale.wizard.mail_compose_message._action_send_mail()

_compute_price_unit_original = SaleOrderLine._compute_price_unit
_action_send_mail_original = MailComposeMessage._action_send_mail


class OfSaleHooks(models.AbstractModel):
    '''When you use monkey patching, the code is executed when the module
    is in the addons_path of the Odoo server, even is the module is not
    installed ! In order to avoid the side-effects it can create,
    we create an AbstractModel inside the module and we test the
    availability of this Model in the code of the monkey patching below.
    '''

    _name = 'of.sale.hooks.installed'
    __doc__ = "This model is used to test if the module is installed and avoid monkey patching side-effects."


@api.depends('product_id', 'product_uom', 'product_uom_qty')
def _compute_price_unit(self):
    """Override of the original method to add to check if the pricelist is quantity dependent."""
    if self.env.get('of.sale.hooks.installed') is None:
        return _compute_price_unit_original(self)
    for line in self:
        # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
        # manually edited
        if line.qty_invoiced > 0:
            continue
        if not line.product_uom or not line.product_id or not line.order_id.pricelist_id:
            line.price_unit = 0.0
        elif (
            (
                not line.order_id.pricelist_id.item_ids  # in v16 pricelist_id.item_ids are empty by default
                or line.order_id.pricelist_id._of_is_quantity_dependent(line.product_id.id, line.order_id.date_order)
            )
            and line.order_id.partner_id
            and (
                not line.price_unit
                or float_compare(line.price_unit, line.product_id.list_price, precision_rounding=2) != 0
            )
        ):
            price = line.with_company(line.company_id)._get_display_price()
            line.price_unit = line.product_id._get_tax_included_unit_price(
                line.company_id,
                line.order_id.currency_id,
                line.order_id.date_order,
                'sale',
                fiscal_position=line.order_id.fiscal_position_id,
                product_price_unit=price,
                product_currency=line.currency_id,
            )


def _action_send_mail(self, auto_commit=False):
    if self.env.get('of.sale.hooks.installed') is None:
        return _action_send_mail_original(self, auto_commit=auto_commit)
    if self.model == 'sale.order':
        self = self.with_context(mailing_document_based=True)
        if self.env.context.get('of_mark_so_as_sent') and self.template_id and not self.template_id.of_copy_to_sender:
            self = self.with_context(mail_notify_author=self.env.user.partner_id in self.partner_ids)
    return super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)


SaleOrderLine._compute_price_unit = _compute_price_unit
MailComposeMessage._action_send_mail = _action_send_mail
