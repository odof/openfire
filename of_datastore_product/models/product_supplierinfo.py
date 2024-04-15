# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


def _of_datastore_is_computed_field(model_obj, field_name):
    """Determine whether a field is a calculated field that can be read from the central database."""
    env = model_obj.env
    field = model_obj._fields[field_name]
    if not field.compute:
        return False
    if field.company_dependent:
        return False
    if not field._description_related:
        return True

    # Traitement particulier des champs related en fonction de la relation
    if model_obj._of_datastore_is_computed_field(field._description_related[0]):
        return True
    f = model_obj._fields[field._description_related[0]]
    for f_name in field._description_related[1:]:
        obj = env[f.comodel_name]
        if not hasattr(obj, "_of_datastore_is_computed_field"):
            # L'objet référencé n'est pas un objet centralisé
            return True
        if obj._of_datastore_is_computed_field(f_name):
            return True
        f = obj._fields[f_name]
    return False


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    @api.model
    def _of_datastore_is_computed_field(self, field_name):
        """Allow to read the relational fields of the articles to this class from the product datastore."""
        return _of_datastore_is_computed_field(self, field_name)
