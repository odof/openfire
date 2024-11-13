# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.of_graphql.graphql.odoo_graphql import many2one, x2many


class OFCalendarEventEquipmentLink(models.Model):
    _inherit = "of.calendar.event.equipment.link"

    @api.model
    def _prepare_mutation_values(self, **args):
        mutation = {}

        if equipment_report_template := args.get("equipment_report_template"):
            mutation["equipment_report_tmpl_id"] = many2one(
                self=self, model="of.equipment.intervention.report.template", input=equipment_report_template
            )

        if task := args.get("task"):
            mutation["task_id"] = many2one(self=self, model="of.planning.task", input=task)

        if equipment := args.get("equipment"):
            mutation["equipment_id"] = many2one(self=self, model="of.equipment", input=equipment)

        if images := args.get("images"):
            mutation["all_image_ids"] = x2many(self=self, model="of.image", input=images)

        if "report_text" in args:
            mutation["report_text"] = args["report_text"]

        return mutation
