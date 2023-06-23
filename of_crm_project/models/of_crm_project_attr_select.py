# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class OFCRMProjectAttrSelect(models.Model):
    _name = 'of.crm.project.attr.select'
    _order = 'attr_id,sequence'

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    attr_id = fields.Many2one(
        'of.crm.project.attr',
        string="Attribute",
        required=True,
        domain="[('type','in',('selection','multiple'))]",
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.multi
    def write(self, vals):
        if 'active' in vals and len(self) == 1 and not self.attr_id.active:
            raise ValidationError("L'attribut associé à cette valeur est désactivé")
        return super(OFCRMProjectAttrSelect, self).write(vals)
