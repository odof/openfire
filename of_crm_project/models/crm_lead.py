# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_template_id = fields.Many2one('of.crm.project.template', string="Project", ondelete="set null")
    of_project_line_ids = fields.One2many('of.crm.project.line', 'lead_id', string="Entrées")
    of_date_project = fields.Date(string="Project date")

    @api.onchange('of_template_id')
    def _onchange_of_template_id(self):
        for opportunity in self:
            if opportunity.of_template_id:
                vals = [(5,)]
                for attr in opportunity.of_template_id.attr_ids:
                    attr_vals = {'attr_id': attr.id, 'type': attr.type, 'name': attr.name, 'sequence': attr.sequence}
                    if attr.type == 'char':
                        attr_vals['val_char'] = attr.val_char_default
                    elif attr.type == 'text':
                        attr_vals['val_text'] = attr.val_text_default
                    elif attr.type == 'selection':
                        attr_vals['val_select_id'] = attr.val_select_id_default
                    else:
                        attr_vals['val_bool'] = attr.val_bool_default
                    vals.append((0, 0, attr_vals))
                opportunity.of_project_line_ids = vals
