# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFCRMProjectAttrSelect(models.Model):
    _name = 'of.crm.project.attr.select'
    _order = 'attr_id, sequence'

    name = fields.Char(string="Name", required=True, translate=True)
    description = fields.Text(string="Description", translate=True)
    attr_id = fields.Many2one(
        comodel_name='of.crm.project.attr',
        string="Attribute",
        required=True,
        domain="[('type', '=', 'selection')]",
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)
