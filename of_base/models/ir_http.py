# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        config_parameter_obj = request.env["ir.config_parameter"].sudo()
        result["of_documentation_url"] = config_parameter_obj.get_param("of.openfire.documentation.url")
        result["of_support_url"] = config_parameter_obj.get_param("of.openfire.support.url")
        return result
