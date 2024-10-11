# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    of_is_intervention_order = fields.Boolean(string="Is intervention order")

    def write(self, vals):
        res = super().write(vals)
        self.env["calendar.event"].action_update_date([("of_order_id", "in", self.ids)])
        return res

    def unlink(self):
        self.env["calendar.event"].action_update_date([("of_order_id", "in", self.ids)])
        return super().unlink()

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = super()._prepare_mutation_values(**args)

        if "of_is_intervention_order" in args:
            mutation["of_is_intervention_order"] = args.get("of_is_intervention_order")
            if args.get("of_is_intervention_order"):
                mutation["require_signature"] = True

        return mutation
