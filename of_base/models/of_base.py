# -*- coding: utf-8 -*-

import threading
import re
import logging

from odoo import models, api, tools, fields, SUPERUSER_ID
from odoo.exceptions import ValidationError, AccessError
from odoo.modules import get_module_resource
from odoo.tools import OrderedSet
from odoo.osv import expression
from odoo.models import regex_order

_logger = logging.getLogger(__name__)

try:
    import phonenumbers
except ImportError:
    _logger.debug(u"Impossible d'importer la librairie Python 'phonenumbers'.")

PHONE_TYPES = [('01_domicile', u"Domicile"),
               ('02_bureau', u"Bureau"),
               ('03_mobile', u"Mobile"),
               ('04_fax', u"Fax")]


def convert_phone_number(value, country_code):
    try:
        res_parse = phonenumbers.parse(value, country_code)
        national_number = str(res_parse.national_number)
        res_parse = phonenumbers.parse(national_number, country_code)
        new_value = phonenumbers.format_number(res_parse, phonenumbers.PhoneNumberFormat.E164)
    except:
        _logger.error(
            u"Impossible de formater le numéro de téléphone '%s' au format international avec le code pays '%s'",
            value, country_code)
        new_value = value
    return new_value


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

    phone = fields.Char(compute='_compute_old_phone_fields', inverse='_set_phone')
    mobile = fields.Char(compute='_compute_old_phone_fields', inverse='_set_mobile')
    fax = fields.Char(compute='_compute_old_phone_fields', inverse='_set_fax')

    of_phone_number_ids = fields.One2many(
        comodel_name='of.res.partner.phone', inverse_name='partner_id', string=u"Numéros de téléphone")

    @api.multi
    def _compute_old_phone_fields(self):
        conv_obj = self.env['of.phone.number.converter']
        for rec in self:
            phone = rec.of_phone_number_ids.filtered(lambda p: p.type == '01_domicile')
            if phone:
                phone = phone[0]
                phone_number = conv_obj.format(phone.number)
                if phone_number.get('national'):
                    rec.phone = phone_number.get('national')
                else:
                    rec.phone = phone.number
            else:
                phone = rec.of_phone_number_ids.filtered(lambda p: p.type == '02_bureau')
                if phone:
                    phone = phone[0]
                    phone_number = conv_obj.format(phone.number)
                    if phone_number.get('national'):
                        rec.phone = phone_number.get('national')
                    else:
                        rec.phone = phone.number
            mobile = rec.of_phone_number_ids.filtered(lambda p: p.type == '03_mobile')
            if mobile:
                mobile = mobile[0]
                phone_number = conv_obj.format(mobile.number)
                if phone_number.get('national'):
                    rec.mobile = phone_number.get('national')
                else:
                    rec.mobile = mobile.number
            fax = rec.of_phone_number_ids.filtered(lambda p: p.type == '04_fax')
            if fax:
                fax = fax[0]
                phone_number = conv_obj.format(fax.number)
                if phone_number.get('national'):
                    rec.fax = phone_number.get('national')
                else:
                    rec.fax = fax.number

    @api.multi
    def _set_phone(self):
        for rec in self:
            country_code = (rec.country_id and rec.country_id.code) or \
                           (self.env.user.company_id.country_id and self.env.user.company_id.country_id.code) or \
                           "FR"
            number = convert_phone_number(rec.phone, country_code)
            # Ne rien faire si le numéro est déjà présent
            if rec.of_phone_number_ids.filtered(lambda p: p.number == number):
                continue
            else:
                # On remplace la valeur actuelle s'il y en a une
                current_phone = rec.of_phone_number_ids.filtered(lambda p: p.type == '01_domicile')
                if current_phone:
                    rec.of_phone_number_ids = [(1, current_phone[0].id, {'number': number})]
                # Sinon on crée le nouveau numéro
                else:
                    rec.of_phone_number_ids = [(0, 0, {'number': number, 'type': '01_domicile'})]

    @api.multi
    def _set_mobile(self):
        for rec in self:
            country_code = (rec.country_id and rec.country_id.code) or \
                           (self.env.user.company_id.country_id and self.env.user.company_id.country_id.code) or \
                           "FR"
            number = convert_phone_number(rec.mobile, country_code)
            # Ne rien faire si le numéro est déjà présent
            if rec.of_phone_number_ids.filtered(lambda p: p.number == number):
                continue
            else:
                # On remplace la valeur actuelle s'il y en a une
                current_phone = rec.of_phone_number_ids.filtered(lambda p: p.type == '03_mobile')
                if current_phone:
                    rec.of_phone_number_ids = [(1, current_phone[0].id, {'number': number})]
                # Sinon on crée le nouveau numéro
                else:
                    rec.of_phone_number_ids = [(0, 0, {'number': number, 'type': '03_mobile'})]

    @api.multi
    def _set_fax(self):
        for rec in self:
            country_code = (rec.country_id and rec.country_id.code) or \
                           (self.env.user.company_id.country_id and self.env.user.company_id.country_id.code) or \
                           "FR"
            number = convert_phone_number(rec.fax, country_code)
            # Ne rien faire si le numéro est déjà présent
            if rec.of_phone_number_ids.filtered(lambda p: p.number == number):
                continue
            else:
                # On remplace la valeur actuelle s'il y en a une
                current_phone = rec.of_phone_number_ids.filtered(lambda p: p.type == '04_fax')
                if current_phone:
                    rec.of_phone_number_ids = [(1, current_phone[0].id, {'number': number})]
                # Sinon on crée le nouveau numéro
                else:
                    rec.of_phone_number_ids = [(0, 0, {'number': number, 'type': '04_fax'})]

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
        return super(ResPartner, self.with_context(of_show_address_line=True)).name_search(name=name, args=args, operator=operator, limit=limit)

    @api.multi
    def name_get(self):
        """ Permet de renvoyer le nom + la ville du client quand valeur du contexte 'of_show_address_line' présent """
        name = self._rec_name
        affichage_ville = self.env['ir.values'].get_default('base.config.settings', 'of_affichage_ville')
        if affichage_ville and self._context.get('of_show_address_line') and name in self._fields:
            result = []
            convert = self._fields[name].convert_to_display_name
            for record in self:
                result.append((record.id, '%s%s' % (convert(record[name], record), ''.join([' (', record.city, ')']) if record.city else '')))
        else:
            result = super(ResPartner, self).name_get()
        return result

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

    # Permet à l'auteur du mail de le recevoir en copie.
    @api.multi
    def _notify(self, message, force_send=False, send_after_commit=True, user_signature=True):
        message_sudo = message.sudo()
        email_channels = message.channel_ids.filtered(lambda channel: channel.email_send)
        # Auparavant, Odoo éliminait l'auteur du mail comme destinataire.
        # On empêche cette éliminination et l'appel du super ajoute les autres destinataires.
        if self._context.get('mail_notify_author'):
            self.sudo().search([
                '|',
                ('id', 'in', self.ids),
                ('channel_ids', 'in', email_channels.ids),
                ('email', '=', message_sudo.author_id and message_sudo.author_id.email or message.email_from),
                ('notify_email', '!=', 'none')])._notify_by_email(message, force_send=force_send, send_after_commit=send_after_commit, user_signature=user_signature)
        return super(ResPartner, self)._notify(message, force_send, send_after_commit, user_signature)


class OFResPartnerPhone(models.Model):
    _name = 'of.res.partner.phone'
    _order = 'type,id'

    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire", index=True, ondelete='cascade')
    number = fields.Char(string="Numéro")
    number_display = fields.Char(
        string="Numéro au format national", compute="_get_number_display", inverse="_set_number_display")
    type = fields.Selection(selection=PHONE_TYPES, string="Type de numéro", required=True)
    title_id = fields.Many2one(
        comodel_name="res.partner.title", string="Civilité du numéro", domain="[('of_used_for_phone', '=', True)]")

    @api.multi
    def _get_number_display(self):
        conv_obj = self.env['of.phone.number.converter']
        for rec in self:
            phone_number = conv_obj.format(rec.number)
            if phone_number.get('national'):
                rec.number_display = phone_number.get('national')
            else:
                rec.number_display = rec.number

    @api.multi
    def _set_number_display(self):
        for rec in self:
            country_code = (rec.partner_id.country_id and rec.partner_id.country_id.code) or \
                           (self.env.user.company_id.country_id and self.env.user.company_id.country_id.code) or \
                           "FR"
            rec.number = convert_phone_number(rec.number_display, country_code)

    @api.model_cr_context
    def _auto_init(self):
        """
        Recover old phone numbers
        """
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.tables WHERE table_name = '%s'" % (self._table,))
        exists = bool(cr.fetchall())
        res = super(OFResPartnerPhone, self)._auto_init()
        if not exists:
            partner_ids = self.env['res.partner'].search([])
            for partner_id in partner_ids:
                phone_number_ids = []
                cr.execute("""  SELECT  phone
                                ,       mobile
                                ,       fax
                                FROM    res_partner
                                WHERE   id          = %s""" % partner_id.id)
                result = cr.fetchone()
                phone = result[0]
                mobile = result[1]
                fax = result[2]
                if phone:
                    number = convert_phone_number(phone, partner_id.country_id and partner_id.country_id.code or "FR")
                    phone_number_ids.append((0, 0, {'number': number, 'type': '01_domicile'}))
                if mobile:
                    number = convert_phone_number(mobile, partner_id.country_id and partner_id.country_id.code or "FR")
                    phone_number_ids.append((0, 0, {'number': number, 'type': '03_mobile'}))
                if fax:
                    number = convert_phone_number(fax, partner_id.country_id and partner_id.country_id.code or "FR")
                    phone_number_ids.append((0, 0, {'number': number, 'type': '04_fax'}))
                partner_id.write({'of_phone_number_ids': phone_number_ids})
        return res

    @api.model
    def create(self, vals):
        if vals.get('number', False):
            partner_id = vals.get('partner_id', False)
            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)
                country_code = (partner.country_id and partner.country_id.code) or \
                    (self.env.user.company_id.country_id and self.env.user.company_id.country_id.code) or \
                    "FR"
            vals['number'] = convert_phone_number(vals.get('number'), country_code)
        return super(OFResPartnerPhone, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('number', False):
            partner = self[0].partner_id
            country_code = (partner.country_id and partner.country_id.code) or \
                (self.env.user.company_id.country_id and self.env.user.company_id.country_id.code) or \
                "FR"
            vals['number'] = convert_phone_number(vals.get('number'), country_code)
        return super(OFResPartnerPhone, self).write(vals)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if args and len(args) == 1 and args[0][0] == 'number':
            if args[0][2] and args[0][2][0] == '0':
                args = [(args[0][0], args[0][1], args[0][2] and args[0][2][1:].replace(" ", "") or '')]

        return super(OFResPartnerPhone, self)._search(args, offset=offset, limit=limit, order=order,
                                                      count=count, access_rights_uid=access_rights_uid)


class ResPartnerTitle(models.Model):
    _inherit = 'res.partner.title'

    of_used_for_phone = fields.Boolean(string="Utilisée pour les numéros de téléphone", default=True)


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

class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    # Store True pour éviter le recalcul lors de l'appui sur n'importe quel bouton.
    of_computed_body = fields.Html(string=u'Contenu calculé', compute='_compute_of_computed_body', sanitize_style=True, strip_classes=True, store=True)

    # Calcul des champs dans mail, mail_compose_message.py : render_message()
    @api.depends()
    def _compute_of_computed_body(self):
        for composer in self:
            composer.of_computed_body = composer.render_message([composer.res_id])[composer.res_id]['body']

    @api.multi
    def button_reload_computed_body(self):
        self._compute_of_computed_body()
        return {"type": "ir.actions.do_nothing"}

    # Permet à l'auteur du mail de le recevoir en copie si le paramètre du modèle est vrai.
    @api.multi
    def send_mail_action(self):
        res = super(MailComposer, self.with_context(mail_notify_author=self.template_id and self.template_id.of_copie_expediteur)).send_mail_action()
        return res

class MailTemplate(models.Model):
    _inherit = 'mail.template'

    of_copie_expediteur = fields.Boolean(string=u"Copie du mail à l'expéditeur")

class ResCompany(models.Model):
    _inherit = "res.company"

    of_juridique = fields.Char(string="Forme juridique")
    of_capital = fields.Char(string="Capital social")
    of_assu_dec = fields.Char(string=u"Assurance décennale")

class BaseConfigSettings(models.TransientModel):

    _inherit = 'base.config.settings'

    @api.model_cr_context
    def _auto_init(self):
        super(BaseConfigSettings, self)._auto_init()
        if not self.env['ir.values'].search([('name', '=', 'of_affichage_ville'), ('model', '=', 'base.config.settings')]):
            self.env['ir.values'].sudo().set_default('base.config.settings', 'of_affichage_ville', True)

    of_affichage_ville = fields.Boolean(
        string="(OF) Afficher ville",
        help=u"Affiche la ville entre parenthèses après le nom du partenaire lors de la recherche de partenaire")

    @api.multi
    def set_of_affichage_ville_defaults(self):
        return self.env['ir.values'].sudo().set_default('base.config.settings', 'of_affichage_ville', self.of_affichage_ville)


class OFPhoneNumberConverter(models.TransientModel):
    _name = 'of.phone.number.converter'

    @api.model
    def format(self, value):
        try:
            phone_number = phonenumbers.parse(value)
            if phone_number:
                return {
                    'international': phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                    'national': phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.NATIONAL),
                }
            else:
                return {
                    'international': None,
                    'national': None,
                }
        except:
            return {
                'international': None,
                'national': None,
            }


OFPhoneNumberConverter()
