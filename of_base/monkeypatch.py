# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree  # nosec - We are not parsing XML from untrusted sources
from lxml.builder import E  # nosec - We are not parsing XML from untrusted sources

from odoo import _, api, models
from odoo.models import BaseModel

from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.addons.base.models.res_partner import Partner
from odoo.addons.base.models.res_users import GroupsView, name_boolean_group, name_selection_groups


# We are 🐒-patching the following methods :
#    - base.user_has_groups()
#    - res.group._update_user_groups_view()
#    - res.partner.onchange_parent_id()
class OfBaseHooks(models.AbstractModel):
    '''When you use monkey patching, the code is executed when the module
    is in the addons_path of the Odoo server, even is the module is not
    installed ! In order to avoid the side-effects it can create,
    we create an AbstractModel inside the module and we test the
    availability of this Model in the code of the monkey patching below.
    '''

    _name = 'of.base.hooks.installed'


# Save the original methods
user_has_groups_original = BaseModel.user_has_groups
_update_user_groups_view_original = GroupsView._update_user_groups_view
onchange_parent_id_original = Partner.onchange_parent_id


@api.model
def user_has_groups(self, groups):
    """Return true if the user is member of at least one of the groups in
    ``groups``, and is not a member of any of the groups in ``groups``
    preceded by ``!``. Typically used to resolve ``groups`` attribute in
    view and model definitions.

    OpenFire Addition: allow use of '+' in the group list to specify
    several groups user must belong to.

    :param str groups: comma-separated list of fully-qualified group
        external IDs, e.g., ``base.group_user,base.group_system``,
        optionally preceded by ``!``
    :return: True if the current user is a member of one of the given groups
        not preceded by ``!`` and is not member of any of the groups
        preceded by ``!``
    """
    if self.env.get('of.base.hooks.installed') is None:
        return user_has_groups_original(self, groups)

    from odoo.http import request

    user = self.env.user

    has_groups = []
    not_has_groups = []
    for group_ext_id in groups.split(','):
        group_ext_id = group_ext_id.strip()
        if group_ext_id[0] == '!' and '+' not in group_ext_id:
            not_has_groups.append(group_ext_id[1:])
        else:
            has_groups.append(group_ext_id)

    for group_ext_id in not_has_groups:
        if group_ext_id == 'base.group_no_one':
            # check: the group_no_one is effective in debug mode only
            if user.has_group(group_ext_id) and request and request.session.debug:
                return False
        else:
            if user.has_group(group_ext_id):
                return False

    for group_ext_id in has_groups:
        for of_group_ext_id in group_ext_id.split('+'):
            of_group_ext_id = of_group_ext_id.strip()
            if of_group_ext_id == 'base.group_no_one':
                # check: the group_no_one is effective in debug mode only
                if not user.has_group(of_group_ext_id) or not request or not request.session.debug:
                    break
            elif of_group_ext_id[0] == '!':
                if user.has_group(of_group_ext_id[1:]):
                    break
            else:
                if not user.has_group(of_group_ext_id):
                    break
        else:
            return True

    return not has_groups


@api.model
def _update_user_groups_view(self):
    """Modify the view with xmlid ``base.user_groups_view``, which inherits
    the user form view, and introduces the reified group fields.
    """
    if self.env.get('of.base.hooks.installed') is None:
        return _update_user_groups_view_original(self)

    # remove the language to avoid translations, it will be handled at the view level
    self = self.with_context(lang=None)

    # We have to try-catch this, because at first init the view does not
    # exist but we are already creating some basic groups.
    view = self.env.ref('base.user_groups_view', raise_if_not_found=False)
    if not (view and view._name == 'ir.ui.view'):
        return

    if self._context.get('install_filename') or self._context.get(MODULE_UNINSTALL_FLAG):
        # use a dummy view during install/upgrade/uninstall
        xml = E.field(name="groups_id", position="after")

    else:
        group_no_one = view.env.ref('base.group_no_one')
        group_employee = view.env.ref('base.group_user')
        xml0, xml1, xml2, xml3, xml4 = [], [], [], [], []
        xml_by_category = {}
        xml1.append(E.separator(string='User Type', colspan="2", groups='base.group_no_one'))

        user_type_field_name = ''
        user_type_readonly = str({})
        sorted_tuples = sorted(
            self.get_groups_by_application(), key=lambda t: t[0].xml_id != 'base.module_category_user_type'
        )
        for app, kind, gs, category_name in sorted_tuples:  # we process the user type first
            attrs = {}
            # hide groups in categories 'Hidden' and 'Extra' (except for group_no_one)
            if app.xml_id in self._get_hidden_extra_categories():
                # MODIF OF
                attrs['groups'] = 'of_base.of_group_root_only'
                # FIN DE MODIF OF

            # User type (employee, portal or public) is a separated group. This is the only 'selection'
            # group of res.groups without implied groups (with each other).
            if app.xml_id == 'base.module_category_user_type':
                # application name with a selection field
                field_name = name_selection_groups(gs.ids)
                # test_reified_groups, put the user category type in invisible
                # as it's used in domain of attrs of other fields,
                # and the normal user category type field node is wrapped in a `groups="base.no_one"`,
                # and is therefore removed when not in debug mode.
                xml0.append(E.field(name=field_name, invisible="1", on_change="1"))
                user_type_field_name = field_name
                user_type_readonly = str({'readonly': [(user_type_field_name, '!=', group_employee.id)]})
                attrs['widget'] = 'radio'
                # Trigger the on_change of this "virtual field"
                attrs['on_change'] = '1'
                xml1.append(E.field(name=field_name, **attrs))
                xml1.append(E.newline())

            elif kind == 'selection':
                # application name with a selection field
                field_name = name_selection_groups(gs.ids)
                attrs['attrs'] = user_type_readonly
                attrs['on_change'] = '1'
                if category_name not in xml_by_category:
                    xml_by_category[category_name] = []
                    xml_by_category[category_name].append(E.newline())
                xml_by_category[category_name].append(E.field(name=field_name, **attrs))
                xml_by_category[category_name].append(E.newline())

            else:
                # application separator with boolean fields
                app_name = app.name or 'Other'
                # MODIF OF
                # masquer la rubrique "Autres"
                if not app.name:
                    attrs['groups'] = 'of_base.of_group_root_only'
                # FIN DE MODIF OF
                xml4.append(E.separator(string=app_name, **attrs))
                left_group, right_group = [], []
                attrs['attrs'] = user_type_readonly
                # we can't use enumerate, as we sometime skip groups
                group_count = 0
                for g in gs:
                    field_name = name_boolean_group(g.id)
                    dest_group = left_group if group_count % 2 == 0 else right_group
                    if g == group_no_one:
                        # make the group_no_one invisible in the form view
                        dest_group.append(E.field(name=field_name, invisible="1", **attrs))
                    else:
                        dest_group.append(E.field(name=field_name, **attrs))
                    group_count += 1
                xml4.append(E.group(*left_group))
                xml4.append(E.group(*right_group))

        xml4.append({'class': "o_label_nowrap"})
        if user_type_field_name:
            user_type_attrs = {'invisible': [(user_type_field_name, '!=', group_employee.id)]}
        else:
            user_type_attrs = {}

        for xml_cat in sorted(xml_by_category.keys(), key=lambda it: it[0]):
            master_category_name = xml_cat[1]
            xml3.append(E.group(*(xml_by_category[xml_cat]), string=master_category_name))

        field_name = 'user_group_warning'
        user_group_warning_xml = E.div(
            {
                'class': "alert alert-warning",
                'role': "alert",
                'colspan': "2",
                'attrs': str({'invisible': [(field_name, '=', False)]}),
            }
        )
        user_group_warning_xml.append(
            E.label(
                {
                    'for': field_name,
                    'string': "Access Rights Mismatch",
                    'class': "text text-warning fw-bold",
                }
            )
        )
        user_group_warning_xml.append(E.field(name=field_name))
        xml2.append(user_group_warning_xml)

        xml = E.field(
            *(xml0),
            E.group(*(xml1), groups="base.group_no_one"),
            E.group(*(xml2), attrs=str(user_type_attrs)),
            E.group(*(xml3), attrs=str(user_type_attrs)),
            E.group(*(xml4), attrs=str(user_type_attrs), groups="base.group_no_one"),
            name="groups_id",
            position="replace",
        )
        xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))

    # serialize and update the view
    xml_content = etree.tostring(xml, pretty_print=True, encoding="unicode")
    if xml_content != view.arch:  # avoid useless xml validation if no change
        new_context = dict(view._context)
        new_context.pop('install_filename', None)  # don't set arch_fs for this computed view
        new_context['lang'] = None
        view.with_context(new_context).write({'arch': xml_content})


@api.onchange('parent_id')
def onchange_parent_id(self):
    if self.env.get('of.base.hooks.installed') is None:
        return onchange_parent_id_original(self)
    # return values in result, as this method is used by _fields_sync()
    if not self.parent_id:
        return
    result = {}
    partner = getattr(self, '_origin', self)
    if partner.parent_id and partner.parent_id != self.parent_id:
        result['warning'] = {
            'title': _('Warning'),
            'message': _(
                'Changing the company of a contact should only be done if it '
                'was never correctly set. If an existing contact starts working for a new '
                'company then a new contact should be created under that new '
                'company. You can use the "Discard" button to abandon this change.'
            ),
        }
    # OPENFIRE : On avait ici un remplacement de l'adresse par celle du parent
    return result


# Replace the original methods with the new ones
BaseModel.user_has_groups = user_has_groups
GroupsView._update_user_groups_view = _update_user_groups_view
Partner.onchange_parent_id = onchange_parent_id
