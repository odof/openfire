# -*- coding: utf-8 -*-

import threading
import re

from odoo import models, api, tools, fields, SUPERUSER_ID
from odoo.exceptions import ValidationError, AccessError
from odoo.modules import get_module_resource
from odoo.tools import OrderedSet
from odoo.osv import expression

class OfReadGroup(models.AbstractModel):
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
            assert gb in fields, "Fields in 'groupby' must appear in the list of fields to read (perhaps it's missing in the list view?)"
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

        data = map(lambda r: {k: self._read_group_prepare_data(k, v, groupby_dict) for k, v in r.iteritems()}, fetched_data)
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

class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    @tools.ormcache('self._uid')
    def context_get(self):
        # Pour désactiver l'envoi des notifications par courriel des changements d'affectation des commandes et factures.
        # On met par défaut dans le contexte des utilisateurs la valeur mail_auto_subscribe_no_notify qui inhibe l'envoi des notifications dans la fonction _message_auto_subscribe_notify() de /addons/mail/models.mail_thread.py.
        result = super(ResUsers, self).context_get()
        result['mail_auto_subscribe_no_notify'] = 1
        return result

    @api.multi
    def write(self, values):
        if SUPERUSER_ID in self._ids and self._uid != SUPERUSER_ID:
            raise AccessError(u'Seul le compte administrateur peut modifier les informations du compte administrateur.')
        return super(ResUsers, self).write(values)

class ResPartner(models.Model):
    _inherit = "res.partner"

    # (fonction temporaire) Supprimer balises html de of_notes_client, ajout du contenu de of_client_notes au champ comment, supprimer la colonne of_client_notes
    @api.model_cr_context
    def _auto_init(self):
        # Teste si le champ of_notes_client existe.
        super(ResPartner, self)._auto_init()
        self._cr.execute(" SELECT * FROM information_schema.columns WHERE table_name = 'res_partner' AND column_name = 'of_notes_client';")
        if bool(self._cr.fetchall()):
            self._cr.execute("SELECT id, of_notes_client, comment FROM res_partner WHERE of_notes_client IS NOT NULL")
            for partner_id, notes, comment in self._cr.fetchall():
                if notes == '<p><br></p>':
                    notes = ""
                if notes:
                    if comment:
                        notes = "<br>---<br>" + notes
                    self._cr.execute("UPDATE res_partner SET comment = CONCAT(comment, '\n', %s) WHERE id = %s;", (notes, partner_id))
            self._cr.execute(u"UPDATE res_partner SET comment = REPLACE(comment, '<em style=\"color: grey;\">Attention, ces notes sont synchronisées entre contacts, devis et plannings d''intervention.</em>', '');")
            self._cr.execute("ALTER TABLE res_partner RENAME COLUMN of_notes_client TO of_notes_client_bck;")

    # Pour afficher l'adresse au format français par défaut quand le pays n'est pas renseigné et non le format US
    @api.multi
    def _display_address(self, without_company=False):
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
        address_format = self.country_id.address_format or \
            "%(street)s\n%(street2)s\n%(zip)s %(city)s\n%(country_name)s"  # Ligne changée par OpenFire
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_id.name or '',
            'company_name': self.commercial_company_name or '',
        }
        for field in self._address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

    # Pour afficher dans le menu déroulant du choix de partenaire l'adresse du contact et pas que le nom.
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self._context.get('show_address'):
            self = self.with_context(of_show_address_line=True)
        return super(ResPartner, self).name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def _get_default_image(self, partner_type, is_company, parent_id):
        # Réécriture de la fonction Odoo pour retirer la couleur de fond aléatoire
        # Ainsi, chaque nouveau partenaire a les mêmes image/image_medium/image_small
        # Ce qui évite de surcharger le filestore
        if getattr(threading.currentThread(), 'testing', False) or self._context.get('install_mode'):
            return False

        colorize, img_path, image = False, False, False

        if partner_type in ['other'] and parent_id:
            parent_image = self.browse(parent_id).image
            image = parent_image and parent_image.decode('base64') or None

        if not image and partner_type == 'invoice':
            img_path = get_module_resource('base', 'static/src/img', 'money.png')
        elif not image and partner_type == 'delivery':
            img_path = get_module_resource('base', 'static/src/img', 'truck.png')
        elif not image and is_company:
            img_path = get_module_resource('base', 'static/src/img', 'company_image.png')
        elif not image:
            img_path = get_module_resource('base', 'static/src/img', 'avatar.png')
            colorize = True

        if img_path:
            with open(img_path, 'rb') as f:
                image = f.read()
        if image and colorize:
            # Un rouge orange, censé rappeler la douce chaleur de la flamme
            # Dans l'âtre, les soirs d'hiver, quand le vent glacial rugit au-dehors
            image = tools.image_colorize(image, False, (250, 150, 0))

        return tools.image_resize_image_big(image.encode('base64'))

    @api.model
    def _add_missing_default_values(self, values):
        # La référence par défaut est celle du parent.
        parent_id = values.get('parent_id')
        if parent_id and isinstance(parent_id, (int, long)) and not values.get('ref') and 'default_ref' not in self._context:
            values['ref'] = self.browse(parent_id).ref
        return super(ResPartner, self)._add_missing_default_values(values)

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        result = super(ResPartner, self).onchange_parent_id()
        if self.parent_id:
            result.setdefault('value', {})['ref'] = self.parent_id.ref
        return result

    @api.model
    def _check_no_ref_duplicate(self, ref):
        if not ref:
            return True
        parent_id = False
        cr = self._cr
        cr.execute("SELECT id,parent_id FROM res_partner WHERE ref = %s", (ref,))
        while True:
            ids = set()
            for id, pid in cr.fetchall():
                if pid:
                    ids.add(pid)
                elif parent_id:
                    if id != parent_id:
                        raise ValidationError(u"Le n° de compte client est déjà utilisé et doit être unique (%s)." % (ref,))
                else:
                    parent_id = id
            if not ids:
                break
            cr.execute("SELECT id,parent_id FROM res_partner WHERE id IN %s", (tuple(ids),))
        return True

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        self._check_no_ref_duplicate(vals.get('ref'))
        return res

    @api.model
    def _update_refs(self, new_ref, partner_refs):
        # Avant de mettre a jour les enfants, on vérifie que les partenaires avec cette référence ont bien tous un parent commun
        self._check_no_ref_duplicate(new_ref)

        to_update_ids = []
        while partner_refs:
            partner, old_ref = partner_refs.pop()
            for child in partner.child_ids:
                if child.ref == old_ref:
                    # La reference du contact était la même que celle du parent, on met à jour et on continue le parcours
                    to_update_ids.append(child.id)
                    partner_refs.append((child, old_ref))
        if to_update_ids:
            self.env['res.partner'].browse(to_update_ids).write({'ref': new_ref})
        return True

    @api.multi
    def write(self, vals):
        # Modification de la fonction write pour propager la modification de la référence aux enfants si besoin
        write_ref = 'ref' in vals
        if write_ref:
            # La référence est modifiée, il va falloir propager la nouvelle valeur aux enfants
            ref = vals['ref']
            partner_refs = [(partner, partner.ref) for partner in self if partner.ref != ref]
        super(ResPartner, self).write(vals)
        if write_ref:
            self._update_refs(ref, partner_refs)
        return True

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

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Recherche multi-mots
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args2 = []
        i = 0
        while i < len(args):
            if args[i] == '|' \
                    and isinstance(args[i + 1], (list)) and args[i + 1][0] == 'default_code' \
                    and isinstance(args[i + 2], (list)) and args[i + 2][0] == 'name' \
                    and args[i+1][1] in ('like', 'ilike') \
                    and args[i + 1][2] == args[i + 2][2]:
                operator = args[i+1][1]
                mots = args[i+1][2].split()
                args2 += ['&'] * (len(mots) - 1)
                for mot in mots:
                    args2 += ['|', ('default_code', operator, mot), ('name', operator, mot)]
                i += 3
            else:
                args2.append(args[i])
                i += 1
        return super(ProductTemplate, self).search(args2, offset=offset, limit=limit, order=order, count=count)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Recherche multi-mots
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args2 = []
        i = 0
        while i < len(args):
            if args[i] == '|' \
                    and isinstance(args[i + 1], (list)) and args[i + 1][0] == 'default_code' \
                    and isinstance(args[i + 2], (list)) and args[i + 2][0] == 'name' \
                    and args[i+1][1] in ('like', 'ilike') \
                    and args[i + 1][2] == args[i + 2][2]:
                operator = args[i+1][1]
                mots = args[i+1][2].split()
                args2 += ['&'] * (len(mots) - 1)
                for mot in mots:
                    args2 += ['|', ('default_code', operator, mot), ('name', operator, mot)]
                i += 3
            else:
                args2.append(args[i])
                i += 1
        return super(ProductProduct, self).search(args2, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            products = self.env['product.product']
            if operator in positive_operators:
                products = self.search([('default_code', '=', name)] + args, limit=limit)
                if not products:
                    products = self.search([('barcode', '=', name)] + args, limit=limit)
            if not products and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Modification OpenFire :
                # Odoo déconseille de mettre ensemble les recherches sur name et default_code à cause de soucis de performance
                # Nous le faisons quand-mêmme pour la recherche partielle sur chacun des deux champs en meme temps
                # Si le temps de calcul devient trop grand, il faudra repenser cette recherche
                products = self.search(args + ['|', ['default_code', operator, name], ['name', operator, name]], limit=limit)
            elif not products and operator in expression.NEGATIVE_TERM_OPERATORS:
                products = self.search(args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit)
            if not products and operator in positive_operators:
                ptrn = re.compile(r'(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    products = self.search([('default_code', '=', res.group(2))] + args, limit=limit)
            # still no results, partner in context: search on supplier info as last hope to find something
            if not products and self._context.get('partner_id'):
                suppliers = self.env['product.supplierinfo'].search([
                    ('name', '=', self._context.get('partner_id')),
                    '|',
                    ('product_code', operator, name),
                    ('product_name', operator, name)])
                if suppliers:
                    products = self.search([('product_tmpl_id.seller_ids', 'in', suppliers.ids)], limit=limit)
        else:
            products = self.search(args, limit=limit)
        return products.name_get()
