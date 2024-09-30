# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if ttype := args.get("ttype"):
            mutation["of_type_id"] = many2one(self=self, model="of.service.request.type", input=ttype)

        if request := args.get("request"):
            mutation["of_request_id"] = many2one(self=self, model="of.service.request", input=request)

        return mutation
