# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import api, models
from odoo.tools.safe_eval import safe_eval


class OFFormReadonly(models.AbstractModel):
    """Allows to set readonly all fields in form view from a domain set in context.
    This is useful when you want to set readonly all fields in a form view depending on a condition.

    In a model you can set a domain in context by inheritance of `_get_view` method:
        ```
        @api.model
        def _get_view(self, view_id=None, view_type='form', **options):
            if self.env.user.has_group('my_module.a_specific_group') and view_type == 'form':
                self = self.with_context(form_readonly="[('state', '=', 'sale')]")
            return super()._get_view(view_id=view_id, view_type=view_type, **options)
        ```
    """

    _name = 'of.form.readonly'
    _description = "OF Form Readonly Abstract Model"

    def process_modifiers_or_attrs(self, node, key, read_only_domain):
        """Process modifiers or attrs of a node to set readonly domain in it."""
        value = node.get(key, {})
        if isinstance(value, str):
            value = safe_eval(value) if key == 'attrs' else json.loads(value)
        if not isinstance(value, dict):
            return

        if (ro_val := value.get('readonly')) and isinstance(ro_val, bool) and ro_val:
            # already readonly nothing to do
            return
        elif (ro_val := value.get('readonly')) and isinstance(ro_val, list):
            # already a domain, we add the read_only_domain
            value['readonly'] = ['|'] + ro_val + safe_eval(read_only_domain)
        elif (ro_val := value.get('readonly')) and isinstance(ro_val, int):
            # readonly="{'readonly': 0}" so we apply the domain
            value['readonly'] = safe_eval(read_only_domain)
        else:
            # apply the domain
            value['readonly'] = safe_eval(read_only_domain)

        if key == 'attrs' and value.get('form_readonly_exception', False):
            return
        return value

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        if (
            arch is not None
            and view_type == 'form'
            and (read_only_domain := self.env.context.get('form_readonly', False))
        ):
            for node in arch.xpath("//field"):
                if modifiers := self.process_modifiers_or_attrs(node, 'modifiers', read_only_domain):
                    node.set('modifiers', f'{modifiers}')
                if attrs := self.process_modifiers_or_attrs(node, 'attrs', read_only_domain):
                    node.set('attrs', f'{attrs}')
        return arch, view
