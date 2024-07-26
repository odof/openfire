# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pack_type = fields.Selection(default='non_detailed', required=True)
    pack_component_price = fields.Selection(selection='_get_pack_component_price', default='totalized', required=True)

    @api.depends(lambda self: self._get_pack_modifiable_invisible_depends())
    def _compute_pack_modifiable_invisible(self):
        """Overridden method for computing the pack modifiable invisible field.
        We removed `detailed` value from `pack_component_price` fields.
        """
        for product in self:
            product.pack_modifiable_invisible = product.pack_type != "detailed"

    @api.onchange('pack_ok', 'pack_component_price', 'pack_line_ids')
    def _onchange_list_price(self):
        if self.pack_ok and self.pack_component_price == 'totalized' and self.pack_line_ids:
            self.list_price = sum(
                pack_line.product_id.list_price * pack_line.quantity for pack_line in self.pack_line_ids
            )
        else:
            self.list_price = 1.0

    @api.onchange('pack_ok', 'pack_component_price', 'pack_line_ids')
    def _onchange_standard_price(self):
        if self.pack_ok and self.pack_component_price == 'totalized' and self.pack_line_ids:
            self.standard_price = sum(
                pack_line.product_id.standard_price * pack_line.quantity for pack_line in self.pack_line_ids
            )
        else:
            self.standard_price = 0.0

    def _get_pack_component_price(self):
        """Method for getting the selection for the pack component price."""
        return [
            ('totalized', _("Calculated")),
            ('ignored', _("Fixed")),
        ]

    def _is_pack_to_be_handled(self):
        """Overridden method for getting if a template is a computable pack.

        We change the way `is_pack` is calculated to take into account `non_detailed` packs with `totalized` prices.
        """
        self.ensure_one()
        is_pack = False
        if self.env.context.get('whole_pack_price'):
            # We could need to check the price of the whole pack (e.g.: e-commerce)
            is_pack = self.pack_ok and self.pack_type == 'detailed' and self.pack_component_price == 'detailed'
        is_pack |= self.pack_ok and (
            (self.pack_type in ['detailed', 'non_detailed'] and self.pack_component_price == 'totalized')
        )
        return is_pack
