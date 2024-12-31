# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class CommentTemplate(models.AbstractModel):
    _inherit = "comment.template"

    of_top_comment_template_id = fields.Many2one(
        comodel_name="base.comment.template",
        string="Top Comment Template",
        domain=lambda self: [("model_ids.model", "=", self._name), ("position", "=", "before_lines")],
    )
    of_bottom_comment_template_id = fields.Many2one(
        comodel_name="base.comment.template",
        string="Bottom Comment Template",
        domain=lambda self: [("model_ids.model", "=", self._name), ("position", "=", "after_lines")],
    )

    of_top_comment = fields.Html(
        string="Top template",
        readonly=False,
        translate=True,
        sanitize=False,
        help="This is the text template that will be inserted into reports.",
    )

    of_bottom_comment = fields.Html(
        string="Bottom template",
        readonly=False,
        translate=True,
        sanitize=False,
        help="This is the text template that will be inserted into reports.",
    )

    @api.onchange("of_top_comment_template_id")
    def _set_of_top_comment(self):
        if self.of_top_comment_template_id:
            new_comment = self.of_top_comment_template_id.text or ""
            self.of_top_comment = (self.of_top_comment or "") + new_comment if self.of_top_comment else new_comment
            self.of_top_comment_template_id = False

    @api.onchange("of_bottom_comment_template_id")
    def _set_of_bottom_comment(self):
        if self.of_bottom_comment_template_id:
            new_comment = self.of_bottom_comment_template_id.text or ""
            self.of_bottom_comment = (
                (self.of_bottom_comment or "") + new_comment if self.of_bottom_comment else new_comment
            )
            self.of_bottom_comment_template_id = False
