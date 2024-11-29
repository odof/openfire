# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast
import json
import logging
from datetime import datetime, timedelta

import pytz

from odoo import Command, _, fields, http
from odoo.http import request
from odoo.tools import plaintext2html
from odoo.tools.float_utils import float_compare

from odoo.addons.of_planning_tour.models.of_planning_tour import DEFAULT_AM_LIMIT_FLOAT
from odoo.addons.resource.models.resource import float_to_time

_logger = logging.getLogger(__name__)


class OFWebsitePlanningBooking(http.Controller):
    @http.route(["/booking"], type="http", auth="public", website=True)
    def booking(self, **kw):
        values = kw

        values["logged"] = True
        values["logged_partner_id"] = request.env.user.partner_id.id
        booking_company_id = self._get_company_id()
        booking_company = request.env["res.company"].browse(booking_company_id)

        if request.env.uid == request.website.user_id.id:
            values["logged"] = False
            values["logged_partner_id"] = 0
            new_customer = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.open_new_customer")
                or False
            )
            if not new_customer:
                # La prise de RDV n'est pas ouverte aux nouveaux clients et l'utilisateur n'est pas connecté
                # -> on le redirige sur la page de connexion
                return request.redirect("/web/login")

        partner = request.env.user.partner_id
        pricelist = partner.property_product_pricelist or request.env.ref("product.list0", False)
        if booking_company.of_booking_specific:
            display_price = booking_company.of_booking_display_price
        else:
            display_price = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.display_price")
                or False
            )
        service_list = []
        for template in request.env["of.planning.intervention.template"].search([]):
            vals = {"id": template.id, "name": template.website_name or template.name}
            if display_price:
                price = self._get_service_price(template.sudo(), False, partner, pricelist)
                vals["name"] = vals["name"] + " - " + "%.2f €" % price
            service_list.append(vals)
        values["service_list"] = service_list

        contract_list = []
        address_list = []
        if values["logged"]:
            contract_type = request.env.ref("of_service.of_service_request_type_maintenance", raise_if_not_found=False)
            contract_list = (
                request.env["of.service.request"]
                .sudo()
                .search(
                    [
                        ("type_id", "=", contract_type.id),  # si pas de contract_type alors erreur
                        ("base_state", "=", "calculated"),
                        ("state", "not in", ("draft", "done", "cancel")),
                        ("recurrency", "=", True),
                        "|",
                        ("partner_id", "child_of", request.env.user.partner_id.id),
                        ("address_id", "child_of", request.env.user.partner_id.id),
                    ]
                )
                .mapped(lambda s: {"id": s.id, "name": s.template_id.website_name or s.template_id.name or s.name})
            )
            address_list.append(
                {
                    "id": request.env.user.partner_id.id,
                    "name": f"{request.env.user.partner_id.zip} - {request.env.user.partner_id.city}",
                }
            )
            address_list += request.env.user.partner_id.child_ids.filtered(
                lambda child: child.zip and child.city
            ).mapped(lambda c: {"id": c.id, "name": f"{c.zip} - {c.city}"})
        values["contract_list"] = contract_list
        values["address_list"] = address_list

        if booking_company.of_booking_specific:
            values["morning_hours_label"] = booking_company.of_booking_morning_hours_label
            values["afternoon_hours_label"] = booking_company.of_booking_afternoon_hours_label
        else:
            values["morning_hours_label"] = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.morning_hours_label")
                or ""
            )
            values["afternoon_hours_label"] = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.afternoon_hours_label")
                or ""
            )

        return request.render("of_website_planning_booking.booking", values)

    @http.route(["/booking/get_partner"], type="json", auth="public", website=True)
    def get_partner(self, partner_id, **kw):
        values = kw

        if "contract_id" in values and values.get("contract_id") != "null":
            service = request.env["of.service.request"].sudo().browse(int(values["contract_id"]))
            partner = service.address_id or service.partner_id
        else:
            partner = request.env["res.partner"].sudo().browse(int(partner_id))

        return json.dumps(
            {
                "id": partner.id,
                "name": partner.name or partner.parent_id.name,
                "email": partner.email or partner.parent_id.email,
                "phone": partner.mobile or partner.parent_id.mobile,
                "street": partner.street,
                "street2": partner.street2,
                "zip": partner.zip,
                "city": partner.city,
            }
        )

    @http.route(["/booking/create_update_partner"], type="json", auth="public", website=True)
    def create_partner(self, partner_id, **kw):
        if not partner_id:
            return self._create_partner()
        else:
            return self._update_partner(int(partner_id))

    @http.route(["/booking/search_slots"], type="json", auth="public", website=True)
    def search_slots(self, service_id, contract_id, partner_id, from_date, search_more=False, **kw):
        result = self._search_slots(
            service_id and int(service_id),
            contract_id and int(contract_id),
            int(partner_id),
            datetime.strptime(from_date, "%Y-%m-%d").date(),
            search_more=search_more,
        )
        return [[{"name": slot.name, "description": slot.description, "id": slot.id} for slot in result[0]], result[1]]

    @http.route(["/booking/confirm"], type="http", auth="public", website=True, methods=["POST"])
    def confirm(self, **kw):
        values = kw
        error = dict()
        validated = False

        if "submitted" in values:
            values.pop("submitted")
            # Champs obligatoires
            if not values.get("terms"):
                error["terms"] = True
            if not values.get("opt_in"):
                error["opt_in"] = True

            if not error:
                validated = True

        values["error_dict"] = error

        # Si il manque les valeurs service_id ET contract_id ou une valeur parmi partner_id, slot_id
        if all(not values.get(key) or values.get(key) == "null" for key in ["service_id", "contract_id"]) or any(
            not values.get(key) or values.get(key) == "null" for key in ["partner_id", "slot_id"]
        ):
            return request.redirect("/booking")

        if validated:
            # Demande de RDV confirmée
            template = service = False
            if values.get("service_id") and values.get("service_id") != "null":
                template = request.env["of.planning.intervention.template"].sudo().browse(int(values["service_id"]))
            elif values.get("contract_id") and values.get("contract_id") != "null":
                service = request.env["of.service.request"].sudo().browse(int(values["contract_id"]))
            partner = request.env["res.partner"].sudo().browse(int(values["partner_id"]))
            website_line = request.env["of.tour.appointment.line.website.wizard"].browse(int(values["slot_id"]))
            intervention_id = self._create_intervention(website_line)
            if intervention_id:
                # Envoyer l'email de confirmation
                mail_template = request.env.ref(
                    "of_website_planning_booking.booking_confirmation_mail_template", raise_if_not_found=False
                )
                if mail_template:
                    mail_template.sudo().send_mail(intervention_id, force_send=True)

                return request.render("of_website_planning_booking.booking_thank_you")
            else:
                return request.redirect("/booking")

        # Arrivée sur la page
        booking_company_id = self._get_company_id()
        booking_company = request.env["res.company"].browse(booking_company_id)
        template = request.env["of.planning.intervention.template"]
        service = request.env["of.service.request"]
        service_name = ""
        if values.get("service_id") and values.get("service_id") != "null":
            template = request.env["of.planning.intervention.template"].sudo().browse(int(values["service_id"]))
            service_name = template.website_name or template.name
        elif values.get("contract_id") and values.get("contract_id") != "null":
            service = request.env["of.service.request"].sudo().browse(int(values["contract_id"]))
            service_name = service.template_id.website_name or service.template_id.name or service.name
        partner = request.env["res.partner"].sudo().browse(int(values["partner_id"]))
        slot = request.env["of.tour.appointment.line.website.wizard"].browse(int(values["slot_id"]))
        if booking_company.of_booking_specific:
            custom_note = booking_company.of_booking_validation_note
            display_price = booking_company.of_booking_display_price
        else:
            custom_note = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.validation_note") or ""
            )
            display_price = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.display_price")
                or False
            )
        # Calcul du prix de la prestation
        price = 0
        if display_price:
            if service:
                display_price = False
            else:
                pricelist = partner.property_product_pricelist or request.env.ref("product.list0", False)
                price = self._get_service_price(template.sudo(), service.sudo(), partner, pricelist)

        values["company"] = request.env["res.company"].sudo().browse(booking_company_id)
        values["partner"] = partner
        values["service_name"] = service_name
        values["display_price"] = display_price
        values["price"] = price
        values["slot"] = slot
        values["custom_note"] = custom_note
        values["terms"] = values.get("terms", False)
        values["opt_in"] = values.get("opt_in", False)

        return request.render("of_website_planning_booking.booking_confirmation", values)

    @http.route(["/booking/error"], type="http", auth="public", website=True)
    def booking_error(self, **kw):
        return request.render("of_website_planning_booking.booking_error")

    def _get_company_id(self):
        # Calcul de la société à prendre en compte
        booking_company_id = (
            request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.intervention_company_id")
            or request.website.company_id.id
        )
        if isinstance(booking_company_id, str):
            booking_company_id = int(booking_company_id)
        if request.env.uid == request.website.user_id.id:
            return booking_company_id
        else:
            booking_use_partner_company = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.use_partner_company")
                or True
            )
            if booking_use_partner_company:
                return request.env.user.partner_id.company_id.id or booking_company_id
            else:
                return booking_company_id

    def _get_service_price(self, template, service, partner, pricelist):
        total_price = 0
        if template:
            lines = template.line_ids
            fiscal_position = template.fiscal_position_id
        else:
            lines = service.line_ids
            fiscal_position = service.fiscal_position_id

        for line in lines:
            price_unit = pricelist._get_product_price(line.product_id, line.qty)
            taxes = line.product_id.taxes_id
            if partner.company_id:
                taxes = taxes.filtered(lambda r: r.company_id == partner.company_id)
            taxes = fiscal_position.map_tax(taxes) or taxes
            amounts = taxes.compute_all(
                price_unit, pricelist.currency_id, line.qty, product=line.product_id, partner=partner
            )
            total_price += amounts["total_included"]

        return total_price

    def _create_partner(self):
        partner_obj = request.env["res.partner"].sudo()
        params = request.params
        vals = {
            "name": params.get("name"),
            "email": params.get("email"),
            "mobile": params.get("phone"),
            "street": params.get("street"),
            "street2": params.get("street2"),
            "zip": params.get("zip"),
            "city": params.get("city"),
        }
        if request.env.uid != request.website.user_id.id:
            vals["parent_id"] = request.env.user.partner_id.id
            vals["company_id"] = request.env.user.partner_id.company_id.id
        else:
            vals["company_id"] = self._get_company_id()
        partner = partner_obj.create(vals)
        partner.geo_localize()
        return partner.id

    def _update_partner(self, partner_id):
        partner_obj = request.env["res.partner"].sudo()
        partner = partner_obj.browse(partner_id)
        params = request.params
        update_vals = {}
        if params["name"] != partner.name or (partner.parent_id and params["name"] != partner.parent_id.name):
            update_vals["name"] = params["name"]
        if params["email"] != partner.email or (partner.parent_id and params["email"] != partner.parent_id.email):
            update_vals["email"] = params["email"]
        if params["phone"] != partner.mobile or (partner.parent_id and params["phone"] != partner.parent_id.mobile):
            update_vals["mobile"] = params["phone"]
        if params["street"] != partner.street:
            update_vals["street"] = params["street"]
        if params["street2"] != partner.street2:
            update_vals["street2"] = params["street2"]
        if params["zip"] != partner.zip:
            update_vals["zip"] = params["zip"]
        if params["city"] != partner.city:
            update_vals["city"] = params["city"]
        if update_vals:
            partner.write(update_vals)
            partner.geo_localize()
        return partner.id

    def _search_slots(self, template_id, service_id, partner_id, from_date, search_more=False):
        # Wizard de recherche
        booking_company_id = self._get_company_id()
        booking_company = request.env["res.company"].browse(booking_company_id)
        if booking_company.of_booking_specific:
            search_type = booking_company.of_booking_search_type
            search_max_criteria = booking_company.of_booking_search_max_criteria
            allow_empty_days = booking_company.of_booking_allow_empty_days
            empty_days_search_type = booking_company.of_booking_empty_days_search_type
            empty_days_search_max_criteria = booking_company.of_booking_empty_days_search_max_criteria
        else:
            search_type = request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.search_type")
            search_max_criteria = float(
                request.env["ir.config_parameter"]
                .sudo()
                .get_param("of.website.planning.booking.search_max_criteria", 0)
            )
            allow_empty_days = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.allow_empty_days")
            )
            empty_days_search_type = (
                request.env["ir.config_parameter"]
                .sudo()
                .get_param("of.website.planning.booking.empty_days_search_type")
            )
            empty_days_search_max_criteria = float(
                request.env["ir.config_parameter"]
                .sudo()
                .get_param("of.website.planning.booking.empty_days_search_max_criteria", 0)
            )
        if search_more and request.session.get("of_booking_wizard_id"):
            # Clic sur le bouton "Chercher plus"
            # Récupération du wizard existant
            wizard_id = request.session.get("of_booking_wizard_id")
            wizard = request.env["of.tour.appointment.wizard"].browse(wizard_id).exists()
            # Le cron de purge des transients a supprimé l'enregistrement
            if not wizard:
                request.session["of_booking_wizard_id"] = False
                return self._search_slots(template_id, service_id, partner_id, from_date, search_more=search_more)
            compute = "more"
            request.session["search_slot_result_nb"] += 10
        else:
            if booking_company.of_booking_specific:
                employee_ids = booking_company.of_booking_employee_ids
                day_ids = booking_company.of_booking_opened_day_ids
                search_mode = booking_company.of_booking_search_mode
            else:
                employee_ids = (
                    request.env["ir.config_parameter"]
                    .sudo()
                    .get_param("of.website.planning.booking.employee_ids", "[]")
                )
                employee_ids = ast.literal_eval(employee_ids)
                if isinstance(employee_ids, int):
                    employee_ids = [employee_ids]
                day_ids = (
                    request.env["ir.config_parameter"]
                    .sudo()
                    .get_param("of.website.planning.booking.opened_day_ids", "[]")
                )
                day_ids = ast.literal_eval(day_ids)
                if isinstance(day_ids, int):
                    day_ids = [day_ids]
                search_mode = (
                    request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.search_mode")
                )

            if template_id:
                service = request.env["of.service.request"]
                template = request.env["of.planning.intervention.template"].browse(template_id)
                task = template.sudo().task_id
            else:
                service = request.env["of.service.request"].sudo().browse(service_id)
                template = service.template_id
                task = service.sudo().task_id

            address_id = partner_id
            customer_id = partner_id
            if request.env.uid != request.website.user_id.id:
                customer_id = request.env.user.partner_id.id

            wizard_vals = {
                "company_id": booking_company_id,
                "partner_id": customer_id,
                "partner_address_id": address_id,
                "template_id": template.id,
                "request_id": service.id,
                "task_id": task.id,
                "start_date_search": from_date,
                "duration": task.duration,
                "day_ids": [Command.set(day_ids)],
                "search_mode": search_mode,
                "search_type": search_type,
            }
            wizard = request.env["of.tour.appointment.wizard"].with_context(of_from_portal=True).create(wizard_vals)
            wizard.sudo().pre_employee_ids = [Command.set(employee_ids)]
            wizard._compute_stop_date_search()
            request.session["of_booking_wizard_id"] = wizard.id
            compute = "new"
            request.session["search_slot_result_nb"] = 10

        web_slots = []

        # Nombre de jours max ouverts à la réservation
        if booking_company.of_booking_specific:
            max_days = booking_company.of_booking_open_days_number
        else:
            max_days = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.open_days_number")
                or 60
            )
            if isinstance(max_days, str):
                max_days = int(max_days)
        max_search_date = fields.Date.today() + timedelta(days=max_days)

        if compute == "new":
            search_end_date = from_date + timedelta(days=14)
            wizard.stop_date_search = min(search_end_date, max_search_date)
            wizard._populate_line_ids(web=True, mode=compute)

        valid_lines = self._filter_slots(
            wizard.line_ids,
            search_type,
            search_max_criteria,
            allow_empty_days,
            empty_days_search_type,
            empty_days_search_max_criteria,
        )

        # Tenter jusqu'à avoir au moins 10 résultats ou ne plus être dans les jours ouverts à la réservation
        while len(valid_lines) < request.session["search_slot_result_nb"] and wizard.stop_date_search < max_search_date:
            new_search_start_date = wizard.stop_date_search + timedelta(days=1)
            new_search_end_date = new_search_start_date + timedelta(days=6)
            wizard.start_date_search = new_search_start_date
            wizard.stop_date_search = min(new_search_end_date, max_search_date)
            wizard._populate_line_ids(web=True, mode="more")
            valid_lines = self._filter_slots(
                wizard.line_ids,
                search_type,
                search_max_criteria,
                allow_empty_days,
                empty_days_search_type,
                empty_days_search_max_criteria,
            )

        if valid_lines:
            web_slots = wizard.build_website_slots(valid_lines)
            # Keep slots of the same day together
            slots_nb = request.session["search_slot_result_nb"]
            if (
                len(web_slots) > slots_nb
                and web_slots[slots_nb - 1].description == _("Morning")
                and web_slots[slots_nb - 1].name == web_slots[slots_nb].name
            ):
                slots_nb += 1
            web_slots = web_slots[0:slots_nb]
        else:
            web_slots = []

        no_more_search = wizard.stop_date_search >= max_search_date

        return [web_slots, not no_more_search]

    def _filter_slots(
        self,
        rdv_lines,
        search_type,
        search_max_criteria,
        allow_empty_days,
        empty_days_search_type,
        empty_days_search_max_criteria,
    ):
        available_lines = rdv_lines.filtered(lambda p: not p.no_geolocated)

        not_empty_day_lines = available_lines.filtered(lambda line: line.sudo().tour_id.tour_line_ids)

        if search_type == "duration":
            valid_lines = not_empty_day_lines.filtered(lambda line: line.useful_duration <= search_max_criteria)
        else:
            valid_lines = not_empty_day_lines.filtered(lambda line: line.useful_distance <= search_max_criteria)

        if allow_empty_days:
            empty_day_lines = available_lines - not_empty_day_lines

            if empty_days_search_type == "duration":
                valid_lines += empty_day_lines.filtered(
                    lambda line: line.useful_duration <= empty_days_search_max_criteria
                )
            else:
                valid_lines += empty_day_lines.filtered(
                    lambda line: line.useful_distance <= empty_days_search_max_criteria
                )

        return valid_lines

    def _create_intervention(self, website_line):
        created = False

        # Fonctionnement basique pour la création : si le créneau backend sélectionné a été rempli entre temps
        # et que le créneau frontend est connecté à d'autre créneaux backend, essayer un autre créneau backend
        while not created and website_line.planning_ids:
            line = website_line.planning_ids.sorted(lambda p: (p.useful_distance))[0]
            line.action_select(sudo=True)

            vals = self._get_intervention_vals(website_line, line)
            try:
                intervention = request.env["calendar.event"].sudo().create(vals)
                created = True
            except Exception as e:
                line.unlink()
                _logger.warning(_("Error during meeting creation in website: %s"), e)

        # Si le créneau front n'est plus connecté à des lignes de wizard, le supprimer
        if not website_line.planning_ids:
            website_line.unlink()

        return intervention.id

    def _get_intervention_vals(self, website_line, line):
        booking_company_id = self._get_company_id()
        booking_company = request.env["res.company"].browse(booking_company_id)
        if booking_company.of_booking_specific:
            default_state = booking_company.of_booking_intervention_state
        else:
            default_state = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.intervention_state")
                or "draft"
            )

        vals = line.wizard_id._prepare_calendar_event_values()

        if request.params.get("comment"):
            vals["description"] = _("Additional notes from customer: <br/>%s") % plaintext2html(
                request.params.get("comment")
            )

        vals.update(
            {
                "of_state": default_state,
                "of_website_create": True,
            }
        )

        # Si le client a choisi un créneau l'après-midi, on doit faire en sorte que le RDV commence après l'heure de
        # coupure
        if website_line.key.endswith("afternoon"):
            employee = line.wizard_id.employee_id.sudo()
            calendar = employee.of_web_resource_calendar_id or employee.resource_calendar_id
            calendar_tz = pytz.timezone(calendar.tz)
            am_limit_float = float(
                request.env["ir.config_parameter"]
                .sudo()
                .get_param("of.planning.tour.tour_am_limit_float", DEFAULT_AM_LIMIT_FLOAT)
            )
            start_date = pytz.utc.localize(vals["start"]).astimezone(calendar_tz)

            if float_compare(am_limit_float, start_date.hour, 5) > 0:
                start_time = float_to_time(am_limit_float)
                vals["start"] = calendar_tz.localize(datetime.combine(start_date.date(), start_time)).astimezone(
                    pytz.utc
                )

        return vals
