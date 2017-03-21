# -*- coding: utf-8 -*-

import openerp
from openerp import models, api,tools
from openerp.osv import osv
from openerp.exceptions import UserError

class OFReadGroup(osv.AbstractModel):
    _name = 'of.readgroup'

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        u"""
        Modification de la classe readgroup pour permettre un ajout de champs personnalisés
        """
        if context is None:
            context = {}
        self.check_access_rights(cr, uid, 'read')
        query = self._where_calc(cr, uid, domain, context=context)
        fields = fields or self._columns.keys()

        groupby = [groupby] if isinstance(groupby, basestring) else groupby
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [
            self._read_group_process_groupby(cr, uid, gb, query, context=context)
            for gb in groupby_list
        ]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(cr, uid, query, 'read', context=context)
        for gb in groupby_fields:
            assert gb in fields, "Fields in 'groupby' must appear in the list of fields to read (perhaps it's missing in the list view?)"
            groupby_def = self._columns.get(gb) or (self._inherit_fields.get(gb) and self._inherit_fields.get(gb)[2])
            # Modif OpenFire : Un champ custom peut ne pas être présent en base de données
            if not getattr(groupby_def, 'of_custom_groupby', False):
                assert groupby_def and groupby_def._classic_write, "Fields in 'groupby' must be regular database-persisted fields (no function or related fields), or function fields with store=True"
                if not (gb in self._fields):
                    # Don't allow arbitrary values, as this would be a SQL injection vector!
                    raise UserError(_('Invalid group_by specification: "%s".\nA group_by specification must be a list of valid fields.') % (gb,))

        aggregated_fields = [
            f for f in fields
            if f not in ('id', 'sequence')
            if f not in groupby_fields
            if f in self._fields
            if self._fields[f].type in ('integer', 'float', 'monetary')
            if getattr(self._fields[f].base_field.column, '_classic_write', False)
        ]

        field_formatter = lambda f: (
            self._fields[f].group_operator or 'sum',
            self._inherits_join_calc(cr, uid, self._table, f, query, context=context),
            f,
        )
        select_terms = ['%s(%s) AS "%s" ' % field_formatter(f) for f in aggregated_fields]

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        groupby_terms, orderby_terms = self._read_group_prepare(cr, uid, order, aggregated_fields, annotated_groupbys, query, context=context)
        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not context.get('group_by_no_leaf')):
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
        cr.execute(query, where_clause_params)
        fetched_data = cr.dictfetchall()

        if not groupby_fields:
            return fetched_data

        # Modif OpenFire : Recherche directe du nom par name_get sur l'objet ciblé
        #  (la méthode standart Odoo procédait par lecture du champ sur l'objet courant,
        #   ce qui est impossible dans le cadre d'un champ one2many)
        for gb in annotated_groupbys:
            if gb['type'] == 'many2one':
                gb_field = gb['field']
                groupby_def = self._columns.get(gb_field) or (self._inherit_fields.get(gb_field) and self._inherit_fields.get(gb_field)[2])
                rel = groupby_def._obj
                gb_obj = self.pool[rel]
                gb_ids = [r[gb_field] for r in fetched_data if r[gb_field]]
                gb_dict = {d[0]: d for d in gb_obj.name_get(cr, uid, gb_ids, context=context)}
                for d in fetched_data:
                    d[gb_field] = gb_dict.get(d[gb_field], False)

        data = map(lambda r: {k: self._read_group_prepare_data(k,v, groupby_dict, context) for k,v in r.iteritems()}, fetched_data)
        result = [self._read_group_format_result(d, annotated_groupbys, groupby, groupby_dict, domain, context) for d in data]
        if lazy and groupby_fields[0] in self._group_by_full:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way
            result = self._read_group_fill_results(cr, uid, domain, groupby_fields[0], groupby[len(annotated_groupbys):],
                                                       aggregated_fields, count_field, result, read_group_order=order,
                                                       context=context)
        return result


# Migration : champs rml_footer2 n'existe plus dans Odoo 8
#class res_company(osv.Model):
#     _name = "res.company"
#     _inherit = "res.company"
# 
#     _columns = {
#         'rml_footer2': fields.char("Pied de page 2e ligne", size=200),
#     }
# 
#     def on_change_header(self, cr, uid, ids, phone, email, fax, website, reg=False, context=None):
#         return {}

# Migration 8 vers 9 : plus email.template
# class email_template(osv.Model):
#     _inherit = 'email.template'
#     _name = "email.template"
# 
#     # Restreint la possibilité d'ajouter/de supprimer une action d'un modèle de courriel aux seuls utilisateurs qui ont les droits de configuration 
#     def create_action(self, cr, uid, ids, context=None):
# #        data_obj = self.pool['ir.model.data']
# #        user_obj = self.pool['res.user']
# #        dummy,group_id = data_obj.get_object_reference(cr, 1, 'base', 'group_user')
# #        group_ids = user_obj.read(cr, uid, uid, ['groups_id'])['groups_id']
#         ir_model_access = self.pool.get('ir.model.access')
#         if not ir_model_access.check_groups(cr, uid, 'base.group_system'):
#             raise osv.except_osv(('Erreur'), "Vous ne pouvez pas effectuer cette action. Assurez-vous d'avoir les droits d'Administration: Configuration" )
#         return super(email_template,self).create_action(cr, SUPERUSER_ID, ids, context=context)
# 
#     def unlink_action(self, cr, uid, ids, context=None):
#         ir_model_access = self.pool.get('ir.model.access')
#         if not ir_model_access.check_groups(cr, uid, 'base.group_system'):
#             raise osv.except_osv(('Erreur'), "Vous ne pouvez pas effectuer cette action. Assurez-vous d'avoir les droits d'Administration: Configuration" )
#         return super(email_template,self).unlink_action(cr, SUPERUSER_ID, ids, context=context)

class ResPartner(models.Model):
    _inherit = "res.partner"

    # Pour afficher l'adresse au format français par défaut quand le pays n'est pas renseigné et non le format US
    def _display_address(self, cr, uid, address, without_company=False, context=None):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''

        # get the information that will be injected into the display format
        # get the address format
        address_format = address.country_id.address_format or \
              "%(street)s\n%(street2)s\n%(zip)s %(city)s\n%(country_name)s" # Ligne changée par OpenFire
        args = {
            'state_code': address.state_id.code or '',
            'state_name': address.state_id.name or '',
            'country_code': address.country_id.code or '',
            'country_name': address.country_id.name or '',
            'company_name': address.parent_name or '',
        }
        for field in self._address_fields(cr, uid, context=context):
            args[field] = getattr(address, field) or ''
        if without_company:
            args['company_name'] = ''
        elif address.parent_id:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

    # Pour afficher dans le menu déroulant de choix de partenaire l'adresse du contact et pas que le nom 
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if context.get('show_address'):
            context = dict(context or {}, of_show_address_line=True)
        return super(ResPartner,self).name_search(cr, uid, name, args, operator, context, limit)
    
    @api.model
    def _get_default_image(self, is_company, colorize=False):
        # Reecriture de la fonction Odoo pour retirer la couleur de fond aleatoire
        # Ainsi, chaque nouveau partenaire a les memes image/image_medium/image_small
        # Ce qui evite de surcharger le filestore
        img_path = openerp.modules.get_module_resource(
            'base', 'static/src/img', 'company_image.png' if is_company else 'avatar.png')
        with open(img_path, 'rb') as f:
            image = f.read()

        # colorize user avatars
        if not is_company:
            # Un rouge orange, cense rappeler la douce chaleur de la flamme
            # Dans l'atre, les soirs d'hiver, quand le vent glacial rugit au dehors
            image = tools.image_colorize(image, False, (250, 150, 0))

        return tools.image_resize_image_big(image.encode('base64'))

    def _add_missing_default_values(self, cr, uid, values, context=None):
        # La reference par defaut est celle du parent
        parent_id = values.get('parent_id')
        if parent_id and isinstance(parent_id, (int,long)) and not values.get('ref') and 'default_ref' not in context:
            values['ref'] = self.read(cr, uid, parent_id, ['ref'], context=context)['ref']
        return super(ResPartner,self)._add_missing_default_values(cr, uid, values, context=context)

    def onchange_parent_id(self, cr, uid, ids, parent_id, context=None):
        result = super(ResPartner, self).onchange_parent_id(cr, uid, ids, parent_id, context=context)
        if parent_id:
            result.setdefault('value', {})['ref'] = self.browse(cr, uid, parent_id, context=context).ref
        return result

    @api.model
    def _check_no_ref_duplicate(self, ref):
        if not ref:
            return True
        parent_id = False
        cr = self._cr
        cr.execute("SELECT id, parent_id FROM res_partner WHERE ref = '%s'" % ref)
        while True:
            vals = cr.fetchall()
            ids = []
            for id, pid in vals:
                if pid:
                    if pid not in ids:
                        ids.append(pid)
                elif parent_id:
                    if id != parent_id:
                        raise osv.except_osv(('Erreur'), u"La référence client est déjà utilisée et doit être unique. (%s)" % (ref,))
                else:
                    parent_id = id
            if not ids:
                break
            cr.execute("SELECT id, parent_id FROM res_partner WHERE id IN %s", (tuple(ids),))
        return True

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        self._check_no_ref_duplicate(vals.get('ref'))
        return res

    @api.model
    def _update_refs(self, new_ref, partner_refs):
        # Avant de mettre a jour les enfants, on verifie que les partenaires avec cette reference ont bien tous un parent commun
        self._check_no_ref_duplicate(new_ref)
        
        to_update_ids = []
        while partner_refs:
            partner, old_ref = partner_refs.pop()
            for child in partner.child_ids:
                if child.ref == old_ref:
                    # La reference du contact etait la meme que celle du parent, on met a jour et on continue le parcours
                    to_update_ids.append(child.id)
                    partner_refs.append((child,old_ref))
        if to_update_ids:
            self.env['res.partner'].browse(to_update_ids).write({'ref':new_ref})
        return True

    @api.multi
    def write(self, vals):
        # Modification de la fonction write pour propager la modification de la reference aux enfants si besoin
        write_ref = 'ref' in vals
        if write_ref:
            # La reference est modifiee, il va falloir propager la nouvelle valeur aux enfants
            ref = vals['ref']
            partner_refs = [(partner,partner.ref) for partner in self if partner.ref != ref]
        super(ResPartner,self).write(vals)
        if write_ref:
            self._update_refs(ref, partner_refs)
        return True
    
    
