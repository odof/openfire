# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    of_template_id = fields.Many2one(comodel_name='of.crm.project.template', string="Project")
    of_project_line_ids = fields.One2many(comodel_name='of.crm.project.line', inverse_name='lead_id', string="Entries")
    of_date_project = fields.Date(string="Project date")

    # Linked Partner fields
    of_interlocutor = fields.Many2one(comodel_name='res.partner', string="Interlocutor")
    of_decision_maker = fields.Many2one(comodel_name='res.partner', string="Decision maker")
    of_architect = fields.Many2one(comodel_name='res.partner', string="Architect")
    of_labor_force = fields.Many2one(comodel_name='res.partner', string="Labor force")
    of_prime_contractor = fields.Many2one(comodel_name='res.partner', string="Prime contractor")
    of_engineering_office = fields.Many2one(comodel_name='res.partner', string="Engineering office")

    @api.onchange('of_template_id')
    def _onchange_of_template_id(self):
        for lead in self:
            if lead.of_template_id:
                lead.update({'of_project_line_ids': [Command.clear()]})
                attr_vals = {}
                vals = []
                for attr in lead.of_template_id.attr_ids:
                    attr_vals['attr_id'] = attr.id
                    attr_vals['type'] = attr.type
                    attr_vals['name'] = attr.name
                    attr_vals['sequence'] = attr.sequence
                    if attr.type == 'char':
                        attr_vals['val_char'] = attr.val_char_default
                    elif attr.type == 'text':
                        attr_vals['val_text'] = attr.val_text_default
                    elif attr.type == 'selection':
                        attr_vals['val_select_id'] = attr.val_select_id_default
                    else:
                        attr_vals['val_bool'] = attr.val_bool_default
                    vals.append(Command.create(attr_vals.copy()))
                lead.update({'of_project_line_ids': vals})
