# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ast import literal_eval


def _get_list_from_parameter(self, key):
    param_value = literal_eval(self.env["ir.config_parameter"].get_param(key, default="[]"))
    return [param_value] if isinstance(param_value, int) else param_value
