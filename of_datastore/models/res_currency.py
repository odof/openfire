# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResCurrency(models.Model):
    _name = "res.currency"
    _inherit = ["res.currency", "of.datastore.model"]

    def of_ds_match_many2one(self, value, base_index, data):
        # on va retourner l'équivalent de cette currency en local
        # on va chercher en local, la devise qui a le même nom et qui est active
        currency_id = self.env["res.currency"].search([("name", "=", value[1])], limit=1)
        return (currency_id.id, currency_id.name) if currency_id else False
