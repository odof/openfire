# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        admins = self.env.ref('base.user_root') | self.env.ref('base.user_admin')
        if self._uid not in admins.ids:
            deposit_categ_id = (
                self.env['ir.config_parameter'].sudo().get_param('of.sale.of_deposit_product_categ_id', False)
            )
            if deposit_categ_id := deposit_categ_id and int(deposit_categ_id) or False:
                deposit_categories = any(vals['categ_id'] == deposit_categ_id for vals in vals_list)
                if deposit_categories:
                    raise UserError(
                        _("Only the administrator has the right to place items in the down payment category.")
                    )
        return super().create(vals_list)

    def write(self, vals):
        admins = self.env.ref('base.user_root') | self.env.ref('base.user_admin')
        if self._uid not in admins.ids:
            deposit_categ_id = (
                self.env['ir.config_parameter'].sudo().get_param('of.sale.of_deposit_product_categ_id', False)
            )
            deposit_categ_id = deposit_categ_id and int(deposit_categ_id) or False
            if deposit_categ_id and vals.get('categ_id') == deposit_categ_id:
                raise UserError(_("Only the administrator has the right to place items in the down payment category."))
            if self.with_context(prefetch_fields=False).search(
                [('id', 'in', self.ids), ('categ_id', '=', deposit_categ_id)], limit=1
            ):
                raise UserError(_("Only the administrator has the right to modify deposit items."))
        return super().write(vals)

    def unlink(self):
        deleted_ids = self.ids
        ir_config_param_obj = self.env['ir.config_parameter'].sudo()
        deposit_product_id = ir_config_param_obj.get_param('sale.default_deposit_product_id')
        res = super().unlink()
        if deposit_product_id in deleted_ids:
            deposit_product_id.set_param('sale.default_deposit_product_id', False)
        return res

    def name_get(self):
        if not self.env.context.get('of_only_default_code'):
            return super().name_get()

        self.browse(self.ids).read(['default_code', 'name'])  # prefetch only required fields
        return [
            (template.id, f'{template.default_code}') if template.default_code else (template.id, f'{template.name}')
            for template in self
        ]
