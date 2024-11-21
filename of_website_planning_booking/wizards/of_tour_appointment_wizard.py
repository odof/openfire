# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import locale

from odoo import fields, models
from odoo.tools.float_utils import float_compare

from odoo.addons.of_planning_tour.models.of_planning_tour import AM_LIMIT_FLOAT

SEARCH_MODES = [
    ("distance", "Distance (km)"),
    ("duree", "Durée (min)"),
]


class OFTourAppointmentWizard(models.TransientModel):
    _inherit = "of.tour.appointment.wizard"

    website_line_ids = fields.One2many(
        comodel_name="of.tour.appointment.line.website.wizard",
        inverse_name="wizard_id",
        string="Website slots Proposals",
    )

    def build_website_slots(self, lines, mode="day"):
        """Construit les créneaux affichés dans le site web, appelée depuis le controller"""

        def format_date(date):
            locale.setlocale(locale.LC_TIME, self.env.user.lang)
            return fields.Date.from_string(date).strftime("%A %d %B %Y").capitalize()

        self.ensure_one()
        am_limit_float = (
            self.env["ir.config_parameter"].sudo().get_param("of.planning.tour.tour_am_limit_float") or AM_LIMIT_FLOAT
        )
        if isinstance(am_limit_float, str):
            am_limit_float = float(am_limit_float)
        compare_precision = 5

        slots_dict = {}
        for slot in lines:
            if mode == "day":
                # création d'un créneau site web
                if slot.date not in slots_dict:
                    slots_dict[slot.date] = {
                        "key": slot.date,
                        "date": slot.date,
                        "ids": [slot.id],
                        "selected": False,
                    }
                else:
                    slots_dict[slot.date]["ids"].append(slot.id)
                if slot.selected:
                    slots_dict[slot.date]["selected"] = True
            elif mode == "half_day":
                # Des créneaux dispo chevauchent souvent l'heure de midi, il faut les ajouter aux créneaux front
                # du matin et de l'après midi si possible
                keys = []
                start_hour = fields.Datetime.context_timestamp(self, slot.available_slot_id.start).hour
                stop_hour = fields.Datetime.context_timestamp(self, slot.available_slot_id.stop).hour
                # il y a de la place entre le début du créneau et l'heure de fin de matinée
                if float_compare(start_hour, am_limit_float - self.duration, compare_precision) <= 0:
                    keys.append(slot.date.strftime("%Y-%m-%d") + "-0-matin")
                # il y a de la place entre l'heure de début d'aprem et la fin du créneau
                if float_compare(stop_hour, am_limit_float + self.duration, compare_precision) >= 0:
                    keys.append(slot.date.strftime("%Y-%m-%d") + "-1-aprem")
                for key in keys:
                    if key not in slots_dict:
                        # créer un nouveau créneau front
                        slots_dict[key] = {
                            "key": key,
                            "date": slot.date,
                            "ids": [slot.id],
                            "selected": False,
                        }
                    else:
                        slots_dict[key]["ids"].append(slot.id)
                    if slot.selected:
                        slots_dict[key]["selected"] = True

        update_vals = [(5,)]
        for k in slots_dict:
            slot = slots_dict[k]
            vals = {}
            vals["key"] = slot["key"]
            vals["name"] = format_date(k)
            if mode == "half_day":
                if k.endswith("matin"):
                    vals["description"] = "Matin"
                else:
                    vals["description"] = "Après-midi"
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
    name = fields.Char(default="DISPONIBLE")
    key = fields.Char()
    date = fields.Date()
    description = fields.Text(string="Slot info", size=128)
    selected = fields.Boolean(string="Selected Slot")

    planning_ids = fields.Many2many(
        string="Employee slots",
        comodel_name="of.tour.appointment.line.wizard",
        relation="of_tour_appointment_line_website_rel",
    )

    # @api.depends('name', 'key', 'date')
    # def _compute_display_name(self):
    #     # le display_name est affiché lors de la confirmation du RDV depuis le portail
    #     lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
    #     for creneau in self:
    #         date_formatted = fields.Date.from_string(creneau.date).strftime('%A ' + lang.date_format)
    #         date_formatted = date_formatted[0].upper() + date_formatted[1:]
    #         if creneau.date == creneau.key:
    #             creneau.display_name = date_formatted
    #         else:
    #             creneau.display_name = u"%s - %s" % (date_formatted, creneau.name)

    # def button_select(self, sudo=False):
    #     """Sélectionne ce créneau en tant que résultat. Appelée depuis le controller"""
    #     self.ensure_one()
    #     line_obj = self.env["of.tournee.rdv.line.website"]
    #     selected_line = line_obj.search([('wizard_id', '=', self.wizard_id.id), ('selected', '=', True)])
    #     selected_line.write({'selected': False})
    #     self.selected = True
    #     # sélectionner le créneau d'intervenant le plus proche au passage
    #     creneau_employee = self.planning_ids.sorted(lambda p: (p.dist_prec, p.dist_ortho_prec))[0]
    #     creneau_employee.button_select(sudo=sudo)
