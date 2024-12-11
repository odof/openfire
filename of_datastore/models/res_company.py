# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = ["res.company", "of.datastore.model"]

    def of_ds_match_many2one(self, value, base_index, data):
        # on va retourner l'équivalent de cette company en local
        return (self.env.company.id, self.env.company.name)
