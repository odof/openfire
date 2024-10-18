# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class OFBaseDocumentLayout(models.AbstractModel):
    """
    Abstract model that defines the common logic for the configuration of the layout of the sale document.
    It mimics `res.config.settings` and is meant to be used in a wizard that is not `res.config.settings`.

    That model is meant to be inherited by the specific document layout configuration models.
    """

    _name = "of.base.document.layout"
    _description = "Base Document Layout"

    @api.model
    def default_get(self, fields_list):
        # just reuse the existing classification of fields in `res.config.settings` to avoid duplicating the logic
        classified_fields = self._get_classified_fields()

        res = super().default_get(fields_list)

        # groups: which groups are implied by the group Employee
        for name, groups, implied_group in classified_fields["group"]:
            res[name] = all(implied_group in group.implied_ids for group in groups)
            if self._fields[name].type == "selection":
                res[name] = str(int(res[name]))  # True, False -> '1', '0'

        # modules: which modules are installed/to install
        for module in classified_fields["module"]:
            res[f"module_{module.name}"] = module.state in ("installed", "to install", "to upgrade")
        return res

    # ---------------------------------------------------------
    # Actions methods
    # ---------------------------------------------------------

    def action_validate_modules(self, modules_fields):
        """Install or uninstall the selected modules."""
        to_install = modules_fields.filtered(lambda m: self[f"module_{m.name}"] and m.state != "installed")
        to_uninstall = modules_fields.filtered(
            lambda m: not self[f"module_{m.name}"] and m.state in ("installed", "to upgrade")
        )

        if to_install or to_uninstall:
            self.env.flush_all()

        if to_uninstall:
            to_uninstall.button_immediate_uninstall()

        installation_status = self._install_modules(to_install)

        if installation_status or to_uninstall:
            # After the uninstall/install calls, the registry and environments
            # are no longer valid. So we reset the environment.
            self.env.reset()
            self = self.env()[self._name]

    def action_validate_groups(self, groups_fields):
        """Apply or remove implied groups based on the value of the group fields."""
        # get the current values of the fields to avoid applying/removing groups unnecessarily
        current_settings = self.default_get(list(self.fields_get()))
        with self.env.norecompute():
            for name, groups, implied_group in sorted(groups_fields, key=lambda k: self[k[0]]):
                groups = groups.sudo()
                implied_group = implied_group.sudo()
                if self[name] == current_settings[name]:
                    continue
                if int(self[name]):
                    groups._apply_group(implied_group)
                else:
                    groups._remove_group(implied_group)

    def action_button_document_layout_save(self):
        self.ensure_one()
        classified_fields = self._get_classified_fields()
        self.action_validate_modules(classified_fields["module"])
        self.action_validate_groups(classified_fields["group"])
        return self.env.context.get("report_action") or {"type": "ir.actions.act_window_close"}

    def _valid_field_parameter(self, field, name):
        return (
            field.type in ("boolean", "selection")
            and name in ("group", "implied_group")
            or super()._valid_field_parameter(field, name)
        )

    # ---------------------------------------------------------
    # Business methods
    # ---------------------------------------------------------

    @api.model
    def _get_classified_fields(self, fnames=None):
        """Classify the fields in the given list into the following categories 'group', 'module' and 'other'.
        {
            'group':   [('group_bar', [browse_group], browse_implied_group), ...],
            'module':  [('module_baz', browse_module), ...],
            'other':   ['foo', 'qux'],
        }
        """
        IrModule = self.env["ir.module.module"]
        IrModelData = self.env["ir.model.data"]
        Groups = self.env["res.groups"]

        def ref(xml_id):
            res_model, res_id = IrModelData._xmlid_to_res_model_res_id(xml_id)
            return self.env[res_model].browse(res_id)

        if fnames is None:
            fnames = self._fields.keys()

        groups, others = [], []
        modules = IrModule
        for name in fnames:
            field = self._fields[name]
            if name.startswith("group_"):
                if field.type not in ("boolean", "selection"):
                    raise Exception("Field %s must have type 'boolean' or 'selection'" % field)
                if not hasattr(field, "implied_group"):
                    raise Exception("Field %s without attribute 'implied_group'" % field)
                field_group_xmlids = getattr(field, "group", "base.group_user").split(",")
                field_groups = Groups.concat(*(ref(it) for it in field_group_xmlids))
                groups.append((name, field_groups, ref(field.implied_group)))
            elif name.startswith("module_"):
                if field.type not in ("boolean", "selection"):
                    raise Exception("Field %s must have type 'boolean' or 'selection'" % field)
                modules += IrModule._get(name[7:])
            else:
                others.append(name)

        return {"group": groups, "module": modules, "other": others}

    @api.model
    def _install_modules(self, modules):
        """Install the requested modules."""
        return (
            to_install_modules.button_immediate_install()
            if (to_install_modules := modules.filtered(lambda module: module.state == "uninstalled"))
            else None
        )
