# -*- coding: utf-8 -*-

from lxml import etree
from lxml.builder import E

from odoo import models, api, tools, fields, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import OrderedSet
from odoo.tools.safe_eval import safe_eval
from odoo.models import BaseModel
from odoo.addons.base.res.res_users import GroupsView, name_boolean_group, name_selection_groups
from odoo.addons.base.res.res_partner import Partner

try:
    import simplejson as json
except ImportError:
    import json


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
            if user.has_group(group_ext_id) and request and request.debug:
                return False
        else:
            if user.has_group(group_ext_id):
                return False

    for group_ext_id in has_groups:
        for of_group_ext_id in group_ext_id.split('+'):
            of_group_ext_id = of_group_ext_id.strip()
            if of_group_ext_id == 'base.group_no_one':
                # check: the group_no_one is effective in debug mode only
                if not user.has_group(of_group_ext_id) or not request or not request.debug:
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


BaseModel.user_has_groups = user_has_groups


@api.model
def _update_user_groups_view(self):
    """
        Remplacement de méthode pour masquer les params de droits du formulaire utilisateur.
        Modify the view with xmlid ``base.user_groups_view``, which inherits
        the user form view, and introduces the reified group fields.
    """
    if self._context.get('install_mode'):
        # use installation/admin language for translatable names in the view
        user_context = self.env['res.users'].context_get()
        self = self.with_context(**user_context)

    # We have to try-catch this, because at first init the view does not
    # exist but we are already creating some basic groups.
    view = self.env.ref('base.user_groups_view', raise_if_not_found=False)
    if view and view.exists() and view._name == 'ir.ui.view':
        group_no_one = view.env.ref('base.group_no_one')
        xml1, xml2 = [], []
        xml1.append(E.separator(string=_('Application'), colspan="2"))
        for app, kind, gs in self.get_groups_by_application():
            # hide groups in categories 'Hidden' and 'Extra' (except for group_no_one)
            attrs = {}
            if app.xml_id in (
                    'base.module_category_hidden', 'base.module_category_extra', 'base.module_category_usability'):
                # MODIF OF
                attrs['groups'] = 'of_base.of_group_root_only'
                # FIN DE MODIF OF

            if kind == 'selection':
                # application name with a selection field
                field_name = name_selection_groups(gs.ids)
                xml1.append(E.field(name=field_name, **attrs))
                xml1.append(E.newline())
            else:
                # application separator with boolean fields
                app_name = app.name or _('Other')
                # MODIF OF
                # masquer la rubrique "Autres"
                if not app.name:
                    attrs['groups'] = 'of_base.of_group_root_only'
                # FIN DE MODIF OF
                xml2.append(E.separator(string=app_name, colspan="4", **attrs))
                for g in gs:
                    field_name = name_boolean_group(g.id)
                    if g == group_no_one:
                        # make the group_no_one invisible in the form view
                        xml2.append(E.field(name=field_name, invisible="1", **attrs))
                    else:
                        xml2.append(E.field(name=field_name, **attrs))

        xml2.append({'class': "o_label_nowrap"})
        xml = E.field(E.group(*(xml1), col="2"), E.group(*(xml2), col="4"), name="groups_id", position="replace")
        xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))
        xml_content = etree.tostring(xml, pretty_print=True, xml_declaration=True, encoding="utf-8")
        if not view.check_access_rights('write', raise_exception=False):
            # erp manager has the rights to update groups/users but not
            # to modify ir.ui.view
            if self.env.user.has_group('base.group_erp_manager'):
                view = view.sudo()
        view.with_context(lang=None).write({'arch': xml_content, 'arch_fs': False})


GroupsView._update_user_groups_view = _update_user_groups_view


@api.onchange('parent_id')
def onchange_parent_id(self):
    # return values in result, as this method is used by _fields_sync()
    if not self.parent_id:
        return
    result = {}
    partner = getattr(self, '_origin', self)
    if partner.parent_id and partner.parent_id != self.parent_id:
        result['warning'] = {
            'title': _('Warning'),
            'message': _('Changing the company of a contact should only be done if it '
                         'was never correctly set. If an existing contact starts working for a new '
                         'company then a new contact should be created under that new '
                         'company. You can use the "Discard" button to abandon this change.')}
    # OPENFIRE : On avait ici un remplacement de l'adresse par celle du parent
    return result


Partner.onchange_parent_id = onchange_parent_id


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    of_custom_groupby = fields.Boolean(string=u"Autorisation forcée pour le regroupement")


class OfReadGroup(models.AbstractModel):
    """
    Cette classe permet d'effectuer un read_group sur un champ qui ne serait normalement pas accepté par Odoo.
    Normalement, un read_group ne peut être effectué que sur un champ ayant le paramètre store=True.
    Une classe héritant de of.readgroup peut en plus autoriser cette fonction sur les champs ayant le paramètre
    of_custom_groupby.
    Il faut ensuite surcharger _read_group_process_groupby afin de modifier la query et de retourner les
    éléments nécessaire à son interprétation.
    """
    _name = 'of.readgroup'

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        self.check_access_rights('read')
        query = self._where_calc(domain)
        fields = fields or [f.name for f in self._fields.itervalues() if f.store]

        groupby = [groupby] if isinstance(groupby, basestring) else list(OrderedSet(groupby))
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [self._read_group_process_groupby(gb, query) for gb in groupby_list]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(query, 'read')
        for gb in groupby_fields:
            assert gb in fields, "Fields in 'groupby' must appear in the list of fields to " \
                                 "read (perhaps it's missing in the list view?)"
            assert gb in self._fields, "Unknown field %r in 'groupby'" % gb
            gb_field = self._fields[gb].base_field
            # Modification OpenFire : Un champ custom peut ne pas être présent en base de données
            if not getattr(gb_field, 'of_custom_groupby', False):
                assert gb_field.store and gb_field.column_type, "Fields in 'groupby' must be regular database-persisted fields (no function or related fields), or function fields with store=True"

        aggregated_fields = [
            f for f in fields
            if f != 'sequence'
            if f not in groupby_fields
            for field in [self._fields.get(f)]
            if field
            if field.group_operator
            if field.base_field.store and field.base_field.column_type
        ]

        field_formatter = lambda f: (
            self._fields[f].group_operator,
            self._inherits_join_calc(self._table, f, query),
            f,
        )
        select_terms = ['%s(%s) AS "%s" ' % field_formatter(f) for f in aggregated_fields]

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        groupby_terms, orderby_terms = self._read_group_prepare(order, aggregated_fields, annotated_groupbys, query)
        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not self._context.get('group_by_no_leaf')):
            count_field = groupby_fields[0] if len(groupby_fields) >= 1 else '_'
        else:
            count_field = '_'
        count_field += '_count'

        prefix_terms = lambda prefix, terms: (prefix + " " + ",".join(terms)) if terms else ''
        prefix_term = lambda prefix, term: ('%s %s' % (prefix, term)) if term else ''

        query = """
            SELECT min(%(table)s.id) AS id, count(%(table)s.id) AS %(count_field)s %(extra_fields)s
            FROM %(from)s
            %(where)s
            %(groupby)s
            %(orderby)s
            %(limit)s
            %(offset)s
        """ % {
            'table': self._table,
            'count_field': count_field,
            'extra_fields': prefix_terms(',', select_terms),
            'from': from_clause,
            'where': prefix_term('WHERE', where_clause),
            'groupby': prefix_terms('GROUP BY', groupby_terms),
            'orderby': prefix_terms('ORDER BY', orderby_terms),
            'limit': prefix_term('LIMIT', int(limit) if limit else None),
            'offset': prefix_term('OFFSET', int(offset) if limit else None),
        }
        self._cr.execute(query, where_clause_params)
        fetched_data = self._cr.dictfetchall()

        if not groupby_fields:
            return fetched_data

        # Modif OpenFire : Recherche directe du nom par name_get sur l'objet ciblé
        #  (la méthode standart Odoo procédait par lecture du champ sur l'objet courant,
        #   ce qui est impossible dans le cadre d'un champ one2many)
        for gb in annotated_groupbys:
            if gb['type'] == 'many2one':
                gb_field = gb['field']
                rel = self._fields[gb_field].base_field.comodel_name
                gb_obj = self.env[rel]
                gb_ids = [r[gb_field] for r in fetched_data if r[gb_field]]
                gb_dict = {d[0]: d for d in gb_obj.browse(gb_ids).name_get()}
                for d in fetched_data:
                    d[gb_field] = gb_dict.get(d[gb_field], False)

        data = map(
            lambda r: {k: self._read_group_prepare_data(k, v, groupby_dict) for k, v in r.iteritems()}, fetched_data)
        result = [self._read_group_format_result(d, annotated_groupbys, groupby, domain) for d in data]
        if lazy:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way
            result = self._read_group_fill_results(
                domain, groupby_fields[0], groupby[len(annotated_groupbys):],
                aggregated_fields, count_field, result, read_group_order=order,
            )
        return result

    @api.model_cr_context
    def _field_create(self):
        """
        Ajoute la mise à jour de of_custom_groupby dans la table ir_model_fields
        """
        super(OfReadGroup, self)._field_create()
        cr = self._cr
        for field in self._fields.itervalues():
            query = "UPDATE ir_model_fields SET of_custom_groupby=%s WHERE model=%s AND name=%s"
            cr.execute(query, (getattr(field, 'of_custom_groupby', False), self._name, field.name))

    @api.model
    def _generate_order_by_inner(self, alias, order_spec, query, reverse_direction=False, seen=None):
        """
        Fonction identique à la fonction définie dans models.py, à l'exception de la zone spécifiée.
        Permet d'ordonner les résultats d'une requête en fonction de champs avec of_custom_groupby=True.
        Nécessite que la fonction of_custom_groupby_generate_order soit surchargée pour chacun de ces champs.
        """
        if seen is None:
            seen = set()
        self._check_qorder(order_spec)

        order_by_elements = []
        for order_part in order_spec.split(','):
            order_split = order_part.strip().split(' ')
            order_field = order_split[0].strip()
            order_direction = order_split[1].strip().upper() if len(order_split) == 2 else ''
            if reverse_direction:
                order_direction = 'ASC' if order_direction == 'DESC' else 'DESC'
            do_reverse = order_direction == 'DESC'

            field = self._fields.get(order_field)
            if not field:
                raise ValueError(_("Sorting field %s not found on model %s") % (order_field, self._name))

            if order_field == 'id':
                order_by_elements.append('"%s"."%s" %s' % (alias, order_field, order_direction))
            else:
                if field.inherited:
                    field = field.base_field
                if field.store and field.type == 'many2one':
                    key = (field.model_name, field.comodel_name, order_field)
                    if key not in seen:
                        seen.add(key)
                        order_by_elements += self._generate_m2o_order_by(alias, order_field, query, do_reverse, seen)
                elif field.store and field.column_type:
                    qualifield_name = self._inherits_join_calc(alias, order_field, query, implicit=False, outer=True)
                    if field.type == 'boolean':
                        qualifield_name = "COALESCE(%s, false)" % qualifield_name
                    order_by_elements.append("%s %s" % (qualifield_name, order_direction))
                # OF Modification OpenFire
                elif getattr(field, 'of_custom_groupby', False):
                    key = (field.model_name, field.comodel_name, order_field)
                    if key not in seen:
                        seen.add(key)
                        order_by_elements += self.of_custom_groupby_generate_order(
                            alias, order_field, query, do_reverse, seen)
                # Fin modification OpenFire
                else:
                    continue  # ignore non-readable or "non-joinable" fields

        return order_by_elements

    @api.model
    def of_custom_groupby_generate_order(self, alias, order_field, query, do_reverse, seen):
        """
        Fonction à surcharger pour ajouter des jointures dans query et retourner un ordre de tri.
        Le format de retour est le même que celui de _generate_order_by_inner()
        """
        return []


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.multi
    def write(self, vals):
        res = super(ResGroups, self).write(vals)
        # Ne pas autoriser l'ajout d'utilisateurs dans le groupe of_group_root_only
        group_root = self.env.ref('of_base.of_group_root_only', raise_if_not_found=False)
        if group_root and group_root in self and vals.get('users'):
            if not len(group_root.users):
                raise UserError(u"Le compte admin ne peut pas être retiré de ce groupe!")
            if len(group_root.users) > 1 or SUPERUSER_ID not in group_root.users.ids:
                raise UserError(u"Seul le compte admin peut appartenir à ce groupe!")
        return res


class Module(models.Model):
    _inherit = 'ir.module.module'

    @api.multi
    def button_immediate_upgrade(self):
        super(Module, self).button_immediate_upgrade()
        # Dans le cadre d'une mise à jour de module, on souhaite rester sur la page courante.
        # On retourne donc une action de rechargement de la page sans spéficier de menu.
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class ResCompany(models.Model):
    _inherit = "res.company"

    of_juridique = fields.Char(string="Forme juridique")
    of_capital = fields.Char(string="Capital social")
    of_assu_dec = fields.Char(string=u"Assurance décennale")
    of_assu_multi = fields.Char(string=u"Assurance multirisques")
    of_qualif = fields.Char(string=u"Qualifications")
    of_general_id = fields.Char(string=u"ID général")
    of_accounting_id = fields.Char(string=u"ID comptable")

    of_ref_mode = fields.Selection(selection=[
        ('no', u"Ne pas remplir"),
        ('id', u"Utiliser l'id du partenaire"),
    ], string=u"Référence client", required=True, default='no')

    @api.multi
    def write(self, vals):
        if vals.get('of_ref_mode') == 'id':
            # On met à jour les contacts existants qui ont une référence vide
            partners = self.env['res.partner'].with_context(active_test=False).search(
                [('ref', '=', False), ('company_id', 'in', self._ids)])
            for partner in partners:
                if not self.env['res.partner'].with_context(active_test=False).search([('ref', '=', str(partner.id))]):
                    partner.ref = str(partner.id)
                else:
                    i = 2
                    while self.env['res.partner'].with_context(active_test=False).search(
                            [('ref', '=', str(partner.id) + '-' + str(i))]):
                        i += 1
                    partner.ref = str(partner.id) + '-' + str(i)
        return super(ResCompany, self).write(vals)

    @api.model
    def get_company_filter_ids(self):
        u"""
        Cette fonction renvois les informations nécessaires à l'utilisation du bouton de filtrage par société.
        Ce bouton est présent dans les vues calendrier et planning du module of_planning_view.
        Ainsi que le tableau de bord du module ks_dashboard_ninja.
        """
        companies = self.env.user.company_ids
        company_id = self.env.user.company_id.id
        filters = []
        for company in companies:
            fil = {'id': company.id, 'name': company.name}
            if company_id == company.id:
                fil['current'] = True
            filters.append(fil)
        return filters


class BaseConfigSettings(models.TransientModel):

    _inherit = 'base.config.settings'

    @api.model_cr_context
    def _auto_init(self):
        super(BaseConfigSettings, self)._auto_init()
        if not self.env['ir.values'].search(
                [('name', '=', 'of_affichage_ville'), ('model', '=', 'base.config.settings')]):
            self.env['ir.values'].sudo().set_default('base.config.settings', 'of_affichage_ville', True)

    of_affichage_ville = fields.Boolean(
        string="(OF) Afficher ville",
        help=u"Affiche la ville entre parenthèses après le nom du partenaire lors de la recherche de partenaire")
    company_share_partner = fields.Boolean(
        string=u"Partager les clients entre toutes les sociétés",
        help=u"Partagez vos clients avec toutes les sociétés définies dans votre base.\n"
             u"* Coché : Les clients sont visibles par toutes les sociétés, "
             u"même si une société est définie pour le client.\n"
             u"* Non coché : Chaque société ne peut voir que ses clients (clients pour lesquels la société est "
             u"définie). Les clients non reliés à une société sont visibles par toutes les sociétés.")
    of_ref_mode = fields.Selection(related='company_id.of_ref_mode', string=u"(OF) Référence client")

    @api.multi
    def set_of_affichage_ville_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'base.config.settings', 'of_affichage_ville', self.of_affichage_ville)

    @api.model
    def get_default_company_share_partner(self, fields):
        return {
            'company_share_partner': not self.env.ref('of_base.of_base_res_partner_rule').active
        }

    @api.multi
    def set_default_company_share_partner(self):
        partner_rule = self.env.ref('of_base.of_base_res_partner_rule')
        for config in self:
            partner_rule.write({'active': not config.company_share_partner})


class OFFormReadonly(models.AbstractModel):
    _name = 'of.form.readonly'

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context
        res = super(OFFormReadonly, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                          submenu=submenu)

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
