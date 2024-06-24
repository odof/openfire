# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ESBService(models.Model):
    _inherit = "of.esb.service"

    def get_data_email(self, args):
        return []

    def set_data_email(self, args):
        return True
