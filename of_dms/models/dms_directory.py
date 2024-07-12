# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DMSDirectory(models.Model):
    _inherit = "dms.directory"

    active = fields.Boolean(default=True)
    of_code = fields.Char(
        string="Code",
        help="""Usually, the model of the record is enough to find the directory it belongs to.
        But sometimes records from a same model can go to different directories.
        This field is used in this case to differentiate directories""",
    )

    def _get_translated_name(self):
        self.ensure_one()
        return self.name

    def update_dms_directories(self):
        """Fonction récursive pour archiver les dossiers vides"""
        module_to_deactivate = self.filtered(lambda d: not d.count_directories and not d.count_total_files)
        if module_to_deactivate:
            module_to_deactivate.write({"active": False})
            module_to_deactivate.mapped("parent_id").update_dms_directories()
