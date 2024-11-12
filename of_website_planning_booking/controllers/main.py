# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast
import json
from datetime import datetime, timedelta

import pytz

from odoo import Command, fields, http
from odoo.http import request
from odoo.tools.float_utils import float_compare

from odoo.addons.of_planning_tour.models.of_planning_tour import AM_LIMIT_FLOAT
from odoo.addons.of_utils.models.misc import hours_to_strs


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
                    "name": "%s - %s" % (request.env.user.partner_id.zip, request.env.user.partner_id.city),
                }
            )
            address_list += request.env.user.partner_id.child_ids.filtered(
                lambda child: child.zip and child.city
            ).mapped(lambda c: {"id": c.id, "name": "%s - %s" % (c.zip, c.city)})
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
            if values.get("service_id") and values.get("service_id") != "null" and values.get("service_id") != "false":
                template = request.env["of.planning.intervention.template"].sudo().browse(int(values["service_id"]))
            elif (
                values.get("contract_id")
                and values.get("contract_id") != "null"
                and values.get("contract_id") != "false"
            ):
                service = request.env["of.service.request"].sudo().browse(int(values["contract_id"]))
            partner = request.env["res.partner"].sudo().browse(int(values["partner_id"]))
            slot = request.env["of.tour.appointment.line.website.wizard"].browse(int(values["slot_id"]))
            intervention_id = self._create_intervention(slot)
            # Envoyer l'email de confirmation
            mail_template = request.env.ref(
                "of_website_planning_booking.booking_confirmation_mail_template", raise_if_not_found=False
            )
            if mail_template:
                mail_template.sudo().send_mail(intervention_id, force_send=True)

            return request.render("of_website_planning_booking.booking_thank_you")

        # Arrivée sur la page
        booking_company_id = self._get_company_id()
        booking_company = request.env["res.company"].browse(booking_company_id)
        template = request.env["of.planning.intervention.template"]
        service = request.env["of.service.request"]
        service_name = ""
        if values.get("service_id") and values.get("service_id") != "null" and values.get("service_id") != "false":
            template = request.env["of.planning.intervention.template"].sudo().browse(int(values["service_id"]))
            service_name = template.website_name or template.name
        elif values.get("contract_id") and values.get("contract_id") != "null" and values.get("contract_id") != "false":
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
        else:
            search_type = request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.search_type")
            search_max_criteria = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.search_max_criteria")
                or 0
            )
            if isinstance(search_max_criteria, str):
                search_max_criteria = float(search_max_criteria)
            allow_empty_days = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.allow_empty_days")
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
                    request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.employee_ids")
                    or []
                )
                employee_ids = ast.literal_eval(employee_ids)
                if isinstance(employee_ids, int):
                    employee_ids = [employee_ids]
                day_ids = (
                    request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.opened_day_ids")
                    or []
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
            wizard_vals = {
                "company_id": booking_company_id,
                "partner_id": partner_id,
                "partner_address_id": partner_id,
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
            wizard._populate_line_ids(sudo=True, mode=compute)

        valid_lines = self._filter_slots(
            wizard.line_ids, search_type, search_max_criteria, allow_empty_days, wizard.duration
        )

        # Tenter jusqu'à avoir au moins 10 résultats ou ne plus être dans les jours ouverts à la réservation
        while len(valid_lines) < request.session["search_slot_result_nb"] and wizard.stop_date_search < max_search_date:
            new_search_start_date = wizard.stop_date_search + timedelta(days=1)
            new_search_end_date = new_search_start_date + timedelta(days=6)
            wizard.start_date_search = new_search_start_date
            wizard.stop_date_search = min(new_search_end_date, max_search_date)
            wizard._populate_line_ids(sudo=True, mode="more")
            valid_lines = self._filter_slots(
                wizard.line_ids, search_type, search_max_criteria, allow_empty_days, wizard.duration
            )

        if valid_lines:
            web_slots = wizard.build_website_slots(valid_lines, mode="half_day")
            # Keep slots of the same day together
            slots_nb = request.session["search_slot_result_nb"]
            if (
                len(web_slots) > slots_nb
                and web_slots[slots_nb - 1].description == "Matin"
                and web_slots[slots_nb - 1].name == web_slots[slots_nb].name
            ):
                slots_nb += 1
            web_slots = web_slots[0:slots_nb]
        else:
            web_slots = []

        no_more_search = wizard.stop_date_search >= max_search_date

        return [web_slots, not no_more_search]

    def _filter_slots(self, rdv_lines, search_type, search_max_criteria, allow_empty_days, duration):
        if search_type == "duration":
            valid_lines = rdv_lines.filtered(lambda line: line.useful_duration <= search_max_criteria)
        else:
            valid_lines = rdv_lines.filtered(lambda line: line.useful_distance <= search_max_criteria)

        if not allow_empty_days:
            # Check that employee has at least one intervention on the same day
            valid_lines = valid_lines.filtered(lambda line: line.sudo().tour_id.intervention_ids)

        return valid_lines

    def _create_intervention(self, slot):
        # TODO Test de création en parallèle sur le même créneau dispo
        backend_slot = slot.planning_ids.sorted(lambda p: (p.useful_distance))[0]
        result = backend_slot.sudo().action_button_confirm_slot()
        # TODO Maj inter avec infos supplémentaires (cf _get_intervention_vals)
        return result["res_id"]

    def _get_intervention_vals(self, slot, backend_slot, template, service, partner):
        tz = pytz.timezone("Europe/Paris")
        am_limit_float = (
            request.env["ir.config_parameter"].sudo().get_param("of.planning.tour.tour_am_limit_float")
            or AM_LIMIT_FLOAT
        )
        booking_company_id = self._get_company_id()
        booking_company = request.env["res.company"].browse(booking_company_id)
        if booking_company.of_booking_specific:
            default_state = booking_company.of_booking_intervention_state
        else:
            default_state = (
                request.env["ir.config_parameter"].sudo().get_param("of.website.planning.booking.intervention_state")
                or "draft"
            )

        description = ""
        if request.params.get("comment"):
            description = "Commentaires additionnels du client : %s" % request.params.get("comment")

        if template:
            template_id = template.id
            service_id = False
            task = template.tache_id
        else:
            template_id = service.template_id and service.template_id.id
            service_id = service.id
            task = service.tache_id

        partner_id = partner.id
        if request.env.uid != request.website.user_id.id:
            partner_id = request.env.user.partner_id.id

        vals = {
            "name": "Intervention web",
            "partner_id": partner_id,
            "address_id": partner.id,
            "template_id": template_id,
            "service_id": service_id,
            "tache_id": task.id,
            "flexible": task.flexible,
            "employee_ids": [(4, backend_slot.employee_id.id, 0)],
            "duree": task.duree,
            "company_id": booking_company_id,
            "state": default_state,
            "fiscal_position_id": task.fiscal_position_id.id or False,
            "verif_dispo": True,
            "origin_interface": "Portail web",
            "website_create": True,
            "description": description,
        }

        # Le créneau de l'employé peut commencer avant le début d'aprem,
        # on fait donc un max pour s'assurer que le RDV soit pris l'aprem
        if slot.name.lower() == "après-midi":
            if float_compare(am_limit_float, backend_slot.date_flo, 5) <= 0:
                date_start = backend_slot.debut_dt
            # création d'un dt à partir de l'heure de début d'aprem
            # attention /!\ l'employé doit travailler à partir de l'heure de début d'aprem
            # @todo: gérer le cas ou l'employé commence à travailler après l'heure de début d'aprem
            else:
                time_str = hours_to_strs("time", am_limit_float)
                date_start_local = tz.localize(datetime.strptime(slot.date + " %s:00" % time_str, "%Y-%m-%d %H:%M:%S"))
                date_start = date_start_local.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_start = backend_slot.debut_dt
        vals["date"] = date_start
        return vals
