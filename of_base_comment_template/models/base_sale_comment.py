# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BaseCommentTemplate(models.Model):
    _inherit = 'base.comment.template'

    engine = fields.Selection(readonly=True, default='qweb')
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        ondelete='cascade',
        index=True,
        default=lambda self: self.env.company,
        help="If set, the comment template will be available only for the selected company.",
    )

    model_ids = fields.Many2many(
        comodel_name="ir.model",
        compute=False,
        compute_sudo=False,
        string="Models (M2M)",
        help="This comment template will be available on this models. "
        "You can see here only models allowed to set the comment template.",
        search="_search_model_ids",
        domain="[('model', 'in', ['sale.order', 'account.move'])]",
    )

    models = fields.Text(required=False)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override to make some fields non-searchable, non_sortable and non-exportable."""
        res = super().fields_get(allfields=None, attributes=attributes)
        hide = ['partner_ids', 'domain', 'engine', 'models']
        for field in hide:
            res[field]['searchable'] = False  # To Hide Field From Filter
            res[field]['sortable'] = False  # To Hide Field From Group by
            res[field]['exportable'] = False  # To Hide Field From Export List
        return res

    @api.constrains('model_ids')
    def check_models(self):
        """Avoid non-existing or not allowed models (is_comment_template=True)"""
        for item in self.filtered('model_ids'):
            models = item.model_ids
            res = self._get_ir_model_items(models.ids)
            if not res or len(res) != len(models):
                raise ValidationError(
                    _("Some models are not found or not allowed: %s") % ", ".join(models.mapped("model"))
                )

    def _get_ir_model_items(self, model_ids):
        return (
            self.env['ir.model']
            .sudo()
            .search(
                [
                    ('wis_comment_template', '=', True),
                    ('model', '!=', 'comment.template'),
                    ('id', 'in', model_ids),
                ]
            )
        )
