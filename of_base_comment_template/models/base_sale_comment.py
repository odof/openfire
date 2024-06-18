# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BaseCommentTemplate(models.Model):
    _inherit = 'base.comment.template'

    engine = fields.Selection(readonly=True, default='qweb')
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        ondelete='cascade',
        index=True,
        default=lambda self: self.env.company,
        help="If set, the comment template will be available only for the selected " "company.",
    )
    models = fields.Selection(
        selection=[
            ('sale.order', "Sale Order"),
            ('account.move', "Account Move"),
        ],
        required=True,
    )
