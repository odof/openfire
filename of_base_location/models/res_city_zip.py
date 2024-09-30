# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCityZip(models.Model):
    _inherit = "res.city.zip"

    geo_lat = fields.Float(string="Latitude", digits=(16, 5))
    geo_lng = fields.Float(string="Longitude", digits=(16, 5))

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Redefinition of the name_search method to allow the search by city name.
        That to manage the case where the zip code is used by several cities. (for exemple "51300" is used by
        Glannes, Changy, Marolles, etc.)
        """
        if not args:
            args = []
        if name and operator == "ilike":
            splited_value = name.strip().split(" ")
            # search by zip code
            zips = self.search([("name", "=like", f"{splited_value[0]}%")])
            if zips:
                # if we found zip codes, store the city name
                name = " ".join(splited_value[1:])
            elif len(splited_value) > 1:
                # if we didn't find zip codes, search by city name with the last word of the search
                zips = self.search([("name", "=like", f"{splited_value[-1]}%")])
                if zips:
                    # if we found zip codes, store the city name
                    name = " ".join(splited_value[:-1])

            if zips:
                # if we found zip codes, search by city name
                zips = self.search([("id", "in", zips._ids), ("city_id.name", "ilike", name)] + args)
                return zips.name_get()
        return super().name_search(name=name, args=args, operator=operator, limit=limit)
