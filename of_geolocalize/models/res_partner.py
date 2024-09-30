# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import _, api, fields, models
from odoo.tools import config

OPENSTREETMAP_PRECISION = [
    ("manual", "Manual"),
    ("excellent", "Excellent"),
    ("high", "High"),
    ("medium", "Medium"),
    ("low", "Low"),
    ("unknown", "Unknown"),
]

GEOCODING_STATE = [
    ("not_tried", "Not Tried"),
    ("success", "Success"),
    ("failure", "Failure"),
    ("manual", "Manual"),
    ("no_address", "Without address"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    of_response_json = fields.Text(string="Geolocation response")
    of_geocoding_state = fields.Selection(
        selection=GEOCODING_STATE,
        default="not_tried",
        string="Geocoding State",
        help="State of geocoding",
    )
    of_precision = fields.Selection(
        OPENSTREETMAP_PRECISION, default="unknown", help="Level of geolocalization 's precision", string="Precision"
    )

    # ----------------------------------------------------------
    # CRUD methods
    # ----------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        geocoding_on_create_value = (
            self.env["ir.config_parameter"].sudo().get_param("of.geolocalize.geocoding_on_create")
        )
        if geocoding_on_create_value == "yes":
            partners.geo_localize()
        return partners

    def write(self, vals):
        geocoding_on_write_value = self.env["ir.config_parameter"].sudo().get_param("of.geolocalize.geocoding_on_write")
        to_update = self.env["res.partner"]
        if any(
            field in vals
            for field in (
                "street",
                "street2",
                "zip",
                "city",
                "state_id",
                "country_id",
            )
        ) and any(f"partner_{field}" not in vals for field in ["latitude", "longitude"]):
            for partner in self:
                for key in ("street", "street2", "zip", "city"):
                    if key in vals and partner[key] != vals[key]:
                        to_update |= partner
                        break
                else:
                    for key in ("state_id", "country_id"):
                        if key in vals and partner[key].id != vals[key]:
                            to_update |= partner
                            break
        if any(field in vals for field in ["partner_latitude", "partner_longitude"]):
            for partner in self:
                partner.of_geocoding_state = "manual"
                partner.of_precision = "manual"

        # Reset json in to update of_response_json and of_geocoding_state
        if (
            any(field in vals for field in ["street", "zip", "city", "state_id", "country_id"])
            and any(f"partner_{field}" not in vals for field in ["latitude", "longitude"])
            and geocoding_on_write_value == "yes"
        ):
            vals.update(
                {
                    "of_response_json": "",
                    "of_geocoding_state": "failure",
                    "of_precision": "unknown",
                }
            )
        result = super().write(vals)
        if to_update and geocoding_on_write_value == "yes":
            to_update.geo_localize()
        return result

    # ----------------------------------------------------------
    # Action methods
    # ----------------------------------------------------------

    def action_geolocalize(self):
        return {
            "name": _("Geolocalize"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "of.geo.wizard",
            "view_id": self.env.ref("of_geolocalize.of_geo_wizard_form_view").id,
            "target": "current",
        }

    # ----------------------------------------------------------
    # Business methods
    # ----------------------------------------------------------

    def _determine_precision(self, rank):
        if 28 <= rank <= 30:
            return "excellent"
        elif 26 <= rank <= 27:
            return "high"
        elif 22 <= rank <= 25:
            return "medium"
        elif 1 <= rank <= 3:
            return "unknown"
        else:
            return "low"

    def geo_localize(self):
        """Override to add custom OF fields"""
        if not self._context.get("force_geo_localize") and (
            self._context.get("import_file")
            or any(config[key] for key in ["test_enable", "test_file", "init", "update"])
        ):
            return False
        partners_not_geo_localized = self.env["res.partner"]
        for partner in self.with_context(lang="en_US"):
            if result := self._geo_localize(
                partner.street,
                partner.zip,
                partner.city,
                partner.state_id.name,
                partner.country_id.name,
            ):
                rank = result[2][0]["place_rank"]
                precision = self._determine_precision(rank)
                partner.write(
                    {
                        "partner_latitude": result[0],
                        "partner_longitude": result[1],
                        "date_localization": fields.Date.context_today(partner),
                        "of_response_json": json.dumps(result[2][0], indent=3, sort_keys=True, ensure_ascii=False),
                        "of_geocoding_state": "success",
                        "of_precision": precision,
                    }
                )
                # if partner has children with different address data, we should geolocalize it
                partner._geo_localize_children()
            else:
                partners_not_geo_localized |= partner
        if partners_not_geo_localized:
            self.env["bus.bus"]._sendone(
                self.env.user.partner_id,
                "simple_notification",
                {
                    "title": _("Warning"),
                    "message": _(
                        "No match found for %(partner_names)s address(es).",
                        partner_names=", ".join(partners_not_geo_localized.mapped("name")),
                    ),
                },
            )

    def _geo_localize_children(self):
        """Geolocalize children of partner if they have different address data"""
        self.ensure_one()
        if children_to_localize := self.child_ids.filtered(
            lambda child: child.street != self.street
            or child.street2 != self.street2
            or child.zip != self.zip
            or child.city != self.city
            or child.state_id != self.state_id
            or child.country_id != self.country_id
            or child.partner_latitude == 0.0
            or child.partner_longitude == 0.0
        ):
            children_to_localize.geo_localize()

    def get_geocoding_country(self):
        return (
            (self.country_id and self.country_id.name)
            or (self.env.user.company_id.country_id and self.env.user.company_id.country_id.name)
            or "France"
        )

    def get_addr_params(self):
        """Get address data from db (same format for all geocoders). Used through the geocoding wizard process.
        :return: string containing address data like "street street2, zip city, country"
        """
        if not (self.zip or self.city):
            # Avoid requests with incomplete data
            return ""

        country = self.get_geocoding_country()
        if self.zip and country.upper() == "FRANCE" and not self.zip.strip().isdigit():
            return ""

        address_parts = []
        for parts in [(self.street, self.street2), (self.zip, self.city)]:
            if parts[0] and parts[1]:
                address_parts.append(" ".join([parts[0], parts[1]]))
            elif parts[0]:
                address_parts.append(parts[0])
            elif parts[1]:
                address_parts.append(parts[1])

        params = ", ".join(address_parts) + (f", {country}" if country else "")
        return params.strip(", ")
