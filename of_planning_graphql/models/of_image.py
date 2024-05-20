# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class OFImage(models.Model):
    _inherit = 'of.image'

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if intervention_date := args.get('intervention_date'):
            mutation['intervention_date'] = intervention_date

        if intervention_status := args.get('intervention_status'):
            mutation['intervention_status'] = intervention_status

        if intervention := args.get('intervention'):
            mutation['intervention_id'] = many2one(self=self, model='calendar.event', input=intervention)

        return mutation
