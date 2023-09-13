# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFCRMProjectAttr(models.Model):
    _name = 'of.crm.project.attr'
    _order = 'sequence'

    name = fields.Char(string="Name", required=True, translate=True)
    description = fields.Text(string="Description", translate=True)
    type = fields.Selection(
        selection=[
            ('bool', "Boolean (Yes/No)"),
            ('char', "Short text"),
            ('text', "Long text"),
            ('selection', "Single choice"),
            ('date', "Date"),
        ],
        required=True,
        default='char',
    )
    selection_ids = fields.One2many(comodel_name='of.crm.project.attr.select', inverse_name='attr_id', string="Values")
    template_ids = fields.Many2many(
        comodel_name='of.crm.project.template',
        relation='crm_project_template_attr_rel',
        column1='attr_id',
        column2='template_id',
        string='Projects',
    )
    active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", default=10)

    val_bool_default = fields.Boolean(string="Default value", default=False)
    val_char_default = fields.Char(string="Default value")
    val_text_default = fields.Text(string="Default value")
    val_select_id_default = fields.Many2one(
        comodel_name='of.crm.project.attr.select',
        string="Default value",
        domain="[('attr_id','=',id)]",
    )
