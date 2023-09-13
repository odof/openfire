# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFCRMProjectLine(models.Model):
    _name = 'of.crm.project.line'
    _order = 'sequence'

    name = fields.Char(string="Question", required=True, translate=True)
    lead_id = fields.Many2one(comodel_name='crm.lead', string="Opportunity", required=True, ondelete="cascade")
    company_id = fields.Many2one(comodel_name='res.company', related='lead_id.company_id', store=True, string="Company")
    attr_id = fields.Many2one(
        comodel_name='of.crm.project.attr', string="Attribute", required=True, ondelete="restrict"
    )
    type = fields.Selection(
        [
            ('bool', "Boolean (Yes/No)"),
            ('char', "Short Text"),
            ('text', "Long Text"),
            ('selection', "Single choice"),
            ('date', "Date"),
        ],
        required=True,
        default='char',
    )
    # xml will not display val_bool and val_select_id if type set to 'char'
    val_bool = fields.Boolean(string="Answer")
    val_char = fields.Char(string="Answer")
    val_text = fields.Text(string="Answer")
    val_date = fields.Date(string="Answer")
    val_select_id = fields.Many2one(comodel_name='of.crm.project.attr.select', string="Answer")
    sequence = fields.Integer(string="Sequence", default=10)
    type_var_name = fields.Char(string="Response variable name", compute="_compute_type_var_name")

    is_answered = fields.Boolean(string="Got an answered")
    is_corrected = fields.Boolean(string="Has been corrected", compute='_compute_is_corrected', store=True)
    answer_date = fields.Date(string="Answer date")
    answer_user_id = fields.Many2one(string="Author of answer", comodel_name='res.users')
    answer_orig = fields.Text(string="Original answer")
    answer_orig_date = fields.Date(string="Original answer date")
    answer_orig_user_id = fields.Many2one(string="Original author answer", comodel_name='res.users', readonly=True)
