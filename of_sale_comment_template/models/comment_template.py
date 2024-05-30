# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CommentTemplate(models.AbstractModel):
    _inherit = 'comment.template'

    comment_template_ids = fields.Many2many(domain=lambda self: [('model_ids.model', '=', self._name)])
