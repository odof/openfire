# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFPlanningInterventionSection(models.Model):
    _name = 'of.planning.intervention.section'
    _description = "Sections to display on mobile"
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    ttype = fields.Char(string="Type", required=True)

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if name := args.get('name'):
            mutation['name'] = name

        if ttype := args.get('type'):
            mutation['ttype'] = ttype

        return mutation
