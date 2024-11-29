# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import locale

from odoo import _, fields, models
from odoo.tools.float_utils import float_compare

from odoo.addons.of_planning_tour.models.of_planning_tour import DEFAULT_AM_LIMIT_FLOAT


class OFTourAppointmentWizard(models.TransientModel):
    _inherit = "of.tour.appointment.wizard"

    website_line_ids = fields.One2many(
        comodel_name="of.tour.appointment.line.website.wizard",
        inverse_name="wizard_id",
        string="Website slots Proposals",
    )

    def _create_line_ids(self, available_slots, web=False):
        wizard_line_obj = self.env["of.tour.appointment.line.wizard"]

        for slot in available_slots:
            if (
                (not web and slot.type != "regular")
                or (web and not slot.tour_id.employee_id.of_web_resource_calendar_id and slot.type != "regular")
                or (web and slot.tour_id.employee_id.of_web_resource_calendar_id and slot.type != "web")
            ):
                continue

            wizard_line_obj.create(
                {
                    "available_slot_id": slot.id,
                    "wizard_id": self.id,
                    "template_id": self.template_id.id,
                }
            )

    def build_website_slots(self, lines):
        """Construit les créneaux affichés dans le site web, appelée depuis le controller"""

        def format_date(date):
            locale.setlocale(locale.LC_TIME, self.env.user.lang)
            return fields.Date.from_string(date).strftime("%A %d %B %Y").capitalize()

        self.ensure_one()
        am_limit_float = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("of.planning.tour.tour_am_limit_float", DEFAULT_AM_LIMIT_FLOAT)
        )
        compare_precision = 5

        slots_dict = {}
        for line in lines:
            # Des créneaux dispo chevauchent souvent l'heure de midi, il faut les ajouter aux créneaux front
            # du matin et de l'après midi si possible
            # TEST
            distance_min = line.useful_distance
            keys = []
            start_hour = fields.Datetime.context_timestamp(self, line.available_slot_id.start).hour
            stop_hour = fields.Datetime.context_timestamp(self, line.available_slot_id.stop).hour
            # il y a de la place entre le début du créneau et l'heure de fin de matinée
            if float_compare(start_hour, am_limit_float - self.duration, compare_precision) <= 0:
                keys.append(line.date.strftime("%Y-%m-%d") + "-0-morning")
            # il y a de la place entre l'heure de début d'après-midi et la fin du créneau
            if float_compare(stop_hour, am_limit_float + self.duration, compare_precision) >= 0:
                keys.append(line.date.strftime("%Y-%m-%d") + "-1-afternoon")
            for key in keys:
                if key not in slots_dict:
                    # créer un nouveau créneau front
                    slots_dict[key] = {
                        "key": key,
                        "date": line.date,
                        "ids": [line.id],
                        "selected": False,
                        "distance_min": distance_min,  # TEST
                    }
                else:
                    slots_dict[key]["ids"].append(line.id)
                    # TEST
                    if distance_min < slots_dict[key]["distance_min"]:
                        slots_dict[key]["distance_min"] = distance_min
                if line.selected:
                    slots_dict[key]["selected"] = True

        update_vals = [(5,)]
        for k in slots_dict:
            slot = slots_dict[k]
            vals = {}
            vals["key"] = slot["key"]
            vals["name"] = format_date(k)
            if k.endswith("morning"):
                vals["description"] = _("Morning")
            else:
                vals["description"] = _("Afternoon")
            # TEST
            vals["description"] += "<br/>À %dkm" % slot["distance_min"]
            vals["date"] = slot["date"]
            vals["selected"] = slot["selected"]
            vals["planning_ids"] = [(4, id_p, 0) for id_p in slot["ids"]]
            update_vals.append((0, 0, vals))
        self.sudo().website_line_ids = update_vals
        return self.website_line_ids


class OFTourAppointmentLineWebsite(models.TransientModel):
    _name = "of.tour.appointment.line.website.wizard"
    _description = "Appointment Proposals for website"
    _inherit = ["of.tour.appointment.line.mixin"]

    wizard_id = fields.Many2one(
        comodel_name="of.tour.appointment.wizard", string="Wizard", required=True, ondelete="cascade", index=True
    )
    name = fields.Char()
    key = fields.Char()
    date = fields.Date()
    description = fields.Text(string="Slot info", size=128)
    selected = fields.Boolean(string="Selected Slot")

    planning_ids = fields.Many2many(
        string="Employee slots",
        comodel_name="of.tour.appointment.line.wizard",
        relation="of_tour_appointment_line_website_rel",
    )
