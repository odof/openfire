# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        move_comment_ids = self._propagate_comments_from_sale_order_to_invoice()
        values.update({'comment_template_ids': [Command.set(move_comment_ids)]})
        return values

    def _propagate_comments_from_sale_order_to_invoice(self):
        """Propagate comments from the sale order to the invoice based on the configuration.
        Returns a list of comment IDs to be set on the invoice.
        """
        propagate_comment_param = (
            self.env['ir.config_parameter'].sudo().get_param('of.sale.comment.template.propagate_comments')
        )
        if propagate_comment_param == 'keep_comments':
            return self._keep_all_comments()
        if propagate_comment_param == 'keep_top_comment':
            return self._keep_top_comments()
        return self._keep_bottom_comments() if propagate_comment_param == 'keep_bottom_comment' else []

    def _filter_existing_invoicing_comment_templates(self, position=None):
        """Filter existing invoicing comment templates based on the given position."""
        domain = [('models', '=', 'account.move')]
        if position:
            domain.append(('position', '=', position))
        return self.env['base.comment.template'].search(domain)

    def _create_invoicing_comment_template(self, order_comment_template):
        """Create an invoicing comment template based on the given order comment template."""
        return (
            self.env['base.comment.template']
            .create(
                {
                    'name': order_comment_template.name,
                    'position': order_comment_template.position,
                    'company_id': order_comment_template.company_id.id,
                    'domain': order_comment_template.domain,
                    'models': 'account.move',
                    'partner_ids': [Command.set(order_comment_template.partner_ids.ids)],
                    'engine': order_comment_template.engine,
                    'text': order_comment_template.text,
                }
            )
            .id
        )

    def _keep_all_comments(self):
        """Return ids of comment templates to be set on the invoice.
        That could be the existing invoicing comment templates or the newly created ones.
        """
        move_comment_ids = []
        invoice_comment_templates = self._filter_existing_invoicing_comment_templates()
        for order_comment_template in self.comment_template_ids:
            if move_comment_template := invoice_comment_templates.filtered(
                lambda move_comment: move_comment.text == order_comment_template.text
            ):
                move_comment_ids.append(move_comment_template.id)
            else:
                move_comment_ids.append(self._create_invoicing_comment_template(order_comment_template))
        return move_comment_ids

    def _keep_top_comments(self):
        return self._get_comment_ids_based_on_position('before_lines')

    def _keep_bottom_comments(self):
        return self._get_comment_ids_based_on_position('after_lines')

    def _get_comment_ids_based_on_position(self, position):
        """Return ids of comment templates to be set on the invoice based on the given position.
        That could be the existing invoicing comment templates or the newly created ones.
        """
        move_comment_ids = []
        invoice_comment_templates = self._filter_existing_invoicing_comment_templates(position)
        for order_comment_template in self.comment_template_ids:
            if move_comment_template := invoice_comment_templates.filtered(
                lambda move_comment: move_comment.text == order_comment_template.text
                and move_comment.position == position
            ):
                move_comment_ids.extend(move_comment_template.id for move_comment_template in move_comment_template)
            elif order_comment_template.position == position:
                move_comment_ids.append(self._create_invoicing_comment_template(order_comment_template))
        return move_comment_ids
