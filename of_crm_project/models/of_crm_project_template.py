# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFCRMProjectTemplate(models.Model):
    _name = 'of.crm.project.template'

    name = fields.Char(string="Name", required=True, translate=True)
    attr_ids = fields.Many2many(
        comodel_name='of.crm.project.attr',
        relation='crm_project_template_attr_rel',
        column1='template_id',
        column2='attr_id',
        string="Attributes",
        help="List of attributes for this template. They will be copied to the project file if this template "
        "is selected.",
    )
    active = fields.Boolean(string="Active", default=True)
