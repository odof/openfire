# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFCRMProjectAttr(models.Model):
    _name = 'of.crm.project.attr'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    type = fields.Selection(
        [
            ('bool', "Booléen (Oui/Non)"),
            ('char', "Texte Court"),
            ('text', "Texte Long"),
            ('selection', "Choix Unique"),
            # ('multiple', "Choix Multiple"), # plus tard
            ('date', "Date"),
        ],
        required=True,
        default='char',
    )
    selection_ids = fields.One2many('of.crm.project.attr.select', 'attr_id', string="Valeurs")
    template_ids = fields.Many2many(
        'of.crm.project.template', 'crm_project_template_attr_rel', 'attr_id', 'template_id', string='Projects'
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    val_bool_default = fields.Boolean(string="Valeur par Défaut", default=False)
    val_char_default = fields.Char(string="Valeur par Défaut")
    val_text_default = fields.Text(string="Valeur par Défaut")
    val_select_id_default = fields.Many2one(
        'of.crm.project.attr.select', string="Default value", domain="[('attr_id','=',id)]", ondelete="set null"
    )

    def write(self, vals):
        super().write(vals)
        if 'active' in vals:
            select_obj = self.env['of.crm.project.attr.select'].with_context(active_test=False)
            select_values = select_obj.search([('attr_id', 'in', self._ids)])
            select_values.write({'active': vals['active']})
        return True
