# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _install_of_equipment_survey(cr, env):
    required_modules = env["ir.module.module"].search(
        [
            ("name", "in", ["of_equipment", "of_planning", "of_survey"]),
        ]
    )
    if any(module.state != "installed" for module in required_modules):
        return

    wanted_modules = env["ir.module.module"].search(
        [("name", "=", "of_equipment_survey"), ("state", "=", "uninstalled")]
    )
    wanted_modules.state = "to install"
    env["base.module.upgrade"].upgrade_module()  # TODO: check if this is the right way to do it


def _install_of_custom_document_equipment(cr, env):
    required_modules = env["ir.module.module"].search(
        [
            ("name", "in", ["of_equipment", "of_planning", "of_custom_document"]),
        ]
    )
    if any(module.state != "installed" for module in required_modules):
        return

    wanted_modules = env["ir.module.module"].search(
        [("name", "=", "of_custom_document_equipment"), ("state", "=", "uninstalled")]
    )
    wanted_modules.state = "to install"
    env["base.module.upgrade"].upgrade_module()  # TODO: check if this is the right way to do it


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Install `of_equipment_survey` if needed
    _install_of_equipment_survey(cr, env)  # FIXME: Not working all the time
    # Install `of_custom_document_equipment` if needed
    _install_of_custom_document_equipment(cr, env)  # FIXME: Not working all the time
