# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import api, models

logger = logging.getLogger(__name__)


class CityZipGeonamesImport(models.TransientModel):
    _inherit = "city.zip.geonames.import"

    @api.model
    def prepare_zip(self, row, city_id):
        vals = super().prepare_zip(row, city_id)
        vals.update(
            {
                "geo_lat": row[9],
                "geo_lng": row[10],
            }
        )
        return vals

    def _process_csv(self, parsed_csv, country):
        """Override of the method to manage the add of the latitude and longitude in the res.city.zip to avoid
        violation of the unique constraint "res_city_zip_name_city_uniq".
        """
        state_model = self.env["res.country.state"]
        zip_model = self.env["res.city.zip"]
        res_city_model = self.env["res.city"]
        # Store current record list
        old_zips = set(zip_model.search([("city_id.country_id", "=", country.id)]).ids)
        search_zips = len(old_zips) > 0
        old_cities = set(res_city_model.search([("country_id", "=", country.id)]).ids)
        search_cities = len(old_cities) > 0
        current_states = state_model.search([("country_id", "=", country.id)])
        search_states = len(current_states) > 0
        max_import = self.env.context.get("max_import", 0)
        logger.info("Starting to create the cities and/or city zip entries")
        # Pre-create states and cities
        state_dict = self._create_states(parsed_csv, search_states, max_import, country)
        city_dict = self._create_cities(parsed_csv, search_cities, max_import, state_dict, country)
        # Zips
        zip_vals_list_check = []  # OpenFire: Manage the add of latitude and longitude
        zip_vals_list = []
        for i, row in enumerate(parsed_csv):
            if max_import and i == max_import:
                break
            # Don't search if there aren't any records
            zip_code = False
            state = state_dict[row[country.geonames_state_code_column or 4]]
            if search_zips:
                zip_code = self._select_zip(row, country, state)
            if not zip_code:
                city_id = city_dict[(self.transform_city_name(row[2], country), state.id)]
                # OpenFire: Manage the add of latitude and longitude
                zip_vals = self.prepare_zip(row, city_id)
                # extract zip and city name to avoid duplicates cause of latitiude and longitude
                zip_vals_check = zip_vals.copy()
                zip_vals_check.pop("geo_lat")
                zip_vals_check.pop("geo_lng")
                if zip_vals_check not in zip_vals_list_check:
                    zip_vals_list_check.append(zip_vals_check)
                    zip_vals_list.append(zip_vals)
                # OpenFire: End
            else:
                old_zips.discard(zip_code.id)
        zip_model.create(zip_vals_list)
        if not max_import:
            if old_zips:
                self._action_remove_old_records("res.city.zip", old_zips, country)
            old_cities -= set(city_dict.values())
            if old_cities:
                self._action_remove_old_records("res.city", old_cities, country)
        logger.info(
            "The wizard to create cities and/or city zip entries from " "geonames has been successfully completed."
        )
        return True
