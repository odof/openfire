# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from lxml import etree
from odoo import api, models
from odoo.tools.safe_eval import safe_eval

try:
    import simplejson as json
except ImportError:
    import json


class OFFormReadonly(models.AbstractModel):
    _name = 'of.form.readonly'

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        read_only_domain = context.get('form_readonly', False)
        if res and read_only_domain:  # Check for context value
            doc = etree.XML(res['arch'])
            if view_type == 'form':  # Applies only for form view
                for node in doc.xpath("//field"):  # All the view fields to readonly
                    modifiers = node.get('modifiers', {})
                    if modifiers and isinstance(modifiers, basestring):
                        modifiers = json.loads(modifiers)
                    if modifiers and isinstance(modifiers, dict) and 'readonly' in modifiers and \
                       isinstance(modifiers.get('readonly', None), bool) and modifiers.get('readonly'):
                        continue
                    elif modifiers and isinstance(modifiers, dict) and 'readonly' in modifiers and isinstance(
                            modifiers.get('readonly', None), list):
                        modifiers['readonly'] = ['|'] + modifiers['readonly'] + safe_eval(read_only_domain)
                    elif modifiers and isinstance(modifiers, dict) and 'readonly' in modifiers and isinstance(
                            modifiers.get('readonly', None), list):
                        if modifiers.get('readonly'):  # gère le cas attrs="{'readonly': 1}"
                            continue
                        else:  # gère le cas attrs="{'readonly': 0}"
                            modifiers['readonly'] = safe_eval(read_only_domain)
                    elif isinstance(modifiers, dict):
                        modifiers['readonly'] = safe_eval(read_only_domain)

                    attrs = node.get('attrs', {})
                    if attrs and isinstance(attrs, basestring):
                        attrs = safe_eval(attrs)
                    if attrs and isinstance(attrs, dict) and attrs.get('form_readonly_exception', False):
                        continue
                    if attrs and isinstance(attrs, dict) and 'readonly' in attrs and \
                       isinstance(attrs.get('readonly', None), bool) and attrs.get('readonly'):
                        continue
                    elif attrs and isinstance(attrs, dict) and 'readonly' in attrs and isinstance(
                            attrs.get('readonly', None), list):
                        attrs['readonly'] = ['|'] + attrs['readonly'] + safe_eval(read_only_domain)
                    elif attrs and isinstance(attrs, dict) and 'readonly' in attrs and isinstance(
                            attrs.get('readonly', None), int):
                        if attrs.get('readonly'):  # gère le cas attrs="{'readonly': 1}"
                            continue
                        else:  # gère le cas attrs="{'readonly': 0}"
                            modifiers['readonly'] = safe_eval(read_only_domain)
                    elif isinstance(modifiers, dict):
                        attrs['readonly'] = safe_eval(read_only_domain)

                    node.set('attrs', json.dumps(attrs))
                    node.set('modifiers', json.dumps(modifiers))
                res['arch'] = etree.tostring(doc)
        return res
