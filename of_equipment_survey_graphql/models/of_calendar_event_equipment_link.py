# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class OFCalendarEventEquipmentLink(models.Model):
    _inherit = "of.calendar.event.equipment.link"

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if survey := args.get("survey"):
            mutation["survey_id"] = many2one(self=self, model="of.survey.survey", input=survey)

        if survey_user_input := args.get("survey_user_input"):
            mutation["survey_user_input_id"] = many2one(
                self=self, model="of.survey.user_input", input=survey_user_input
            )
        return mutation
