# -*- coding: utf-8 -*-

import threading
import re
import logging

from odoo import models, api, tools, fields, SUPERUSER_ID, _
from odoo.exceptions import ValidationError, AccessError
from odoo.modules import get_module_resource
from odoo.tools import OrderedSet
from odoo.osv import expression

_logger = logging.getLogger(__name__)

try:
    import phonenumbers
except ImportError:
    _logger.debug(u"Impossible d'importer la librairie Python 'phonenumbers'.")

PHONE_TYPES = [('01_domicile', u"Domicile"),
               ('02_bureau', u"Bureau"),
               ('03_mobile', u"Mobile"),
               ('04_fax', u"Fax")]


def convert_phone_number(value, default_country_code=None, new_format='e164', strict=False):
    """
    Fonction de conversion de numéro de téléphone
    :param value: Numéro de téléphone fourni.
    :param default_country_code: Code pays par défaut à utiliser pour formater le numéro.
    :param new_format: Format voulu pour la conversion du numéro, au choix entre les valeurs
     'e164', 'national', 'international', 'rfc3966', 'country', None
    :param strict: Si le numéro n'est pas formatable, strict détermine si il doit être retourné
    :return: Retourne le numéro formaté selon le format choisi.
     Si new_format à 'country', retourne au format national si le pays du numéro correspond à default_country_code,
                                retourne au format international sinon
     Si new_format à None/False: retourne un dictionnaire avec les différents formats disponibles.
     Si le formatage échoue, value est retourné sauf si la valeur strict est vraie, auquel cas False est retourné.
    """
    if not value:
        return False
    phone_formats = {
        'e164': phonenumbers.PhoneNumberFormat.E164,
        'national': phonenumbers.PhoneNumberFormat.NATIONAL,
        'international': phonenumbers.PhoneNumberFormat.INTERNATIONAL,
        'rfc3966': phonenumbers.PhoneNumberFormat.RFC3966,
    }
    phone_format = phone_formats.get(new_format)
    result = False if strict else value
    try:
        # On tente d'extraire le numéro de téléphone
        matcher = phonenumbers.PhoneNumberMatcher(value, default_country_code)
        if matcher.has_next():
            number = matcher.next().number
            if phone_format is not None:
                result = phonenumbers.format_number(number, phone_format)
            elif new_format == 'country':
                # On compare le code pays du numéro à celui fourni en entrée
                # pour retourner un format national ou international.
                if phonenumbers.phonenumberutil.region_code_for_number(number) == default_country_code:
                    result = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.NATIONAL)
                else:
                    result = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            else:
                result = {
                    key: phonenumbers.format_number(number, phone_format)
                    for key, phone_format in phone_formats.iteritems()
                }
    except phonenumbers.phonenumberutil.NumberParseException:
        _logger.error(
            u"Impossible de formater le numéro de téléphone '%s' au format international avec le code pays '%s'",
            value, default_country_code)
    return result


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

    @api.model_cr_context
    def _auto_init(self):
        """
        Synchronisation des champs 'customer' et 'supplier' entre les contacts enfants physiques et leur parent
        """
        res = super(ResPartner, self)._auto_init()
        cr = self._cr
        cr.execute("""  UPDATE  res_partner     RP
                        SET     customer        = RP1.customer
                        ,       supplier        = RP1.supplier
                        FROM    res_partner     RP1
                        WHERE   RP.parent_id    IS NOT NULL
                        AND     RP.is_company   = False
                        AND     RP1.id          = RP.parent_id""")
        return res

    phone = fields.Char(compute='_compute_old_phone_fields', inverse='_inverse_phone')
    mobile = fields.Char(compute='_compute_old_phone_fields', inverse='_inverse_mobile')
    fax = fields.Char(compute='_compute_old_phone_fields', inverse='_inverse_fax')
    of_phone_number_ids = fields.One2many(
        comodel_name='of.res.partner.phone', inverse_name='partner_id', string=u"Numéros de téléphone")
    of_phone_error = fields.Boolean(
        string=u"Numéros de téléphone mal formatés", compute="_compute_of_phone_error", search="_search_of_phone_error")
    of_parent_category_id = fields.Many2many('res.partner.category', string=u"Étiquettes parent",
                                             compute="_compute_parent_category")

    @api.multi
    def _compute_old_phone_fields(self):
        user = self.env.user
        default_country = user.country_id or user.company_id.country_id
        default_country_code = default_country and default_country.code or 'FR'
        for rec in self:
            phone = rec.of_phone_number_ids.filtered(lambda p: p.type == '01_domicile')
            if not phone:
                phone = rec.of_phone_number_ids.filtered(lambda p: p.type == '02_bureau')
            if phone:
                rec.phone = convert_phone_number(phone[0].number, default_country_code, new_format='country')
            mobile = rec.of_phone_number_ids.filtered(lambda p: p.type == '03_mobile')
            if mobile:
                rec.mobile = convert_phone_number(mobile[0].number, default_country_code, new_format='country')
            fax = rec.of_phone_number_ids.filtered(lambda p: p.type == '04_fax')
            if fax:
                rec.fax = convert_phone_number(fax[0].number, default_country_code, new_format='country')

    @api.depends('parent_id', 'parent_id.category_id')
    def _compute_parent_category(self):
        for partner in self:
            parent = partner
            while parent.parent_id:
                parent = parent.parent_id
            if not isinstance(parent.id, models.NewId):
                partners = self.search([('id', 'child_of', parent.id)])
                partners -= partner
                partner.of_parent_category_id = partners.mapped('category_id')

    @api.multi
    def _of_set_number(self, number_field, number_type):
        user = self.env.user
        default_country = user.country_id or user.company_id.country_id
        default_country_code = default_country and default_country.code or 'FR'
        for rec in self:
            number = convert_phone_number(rec[number_field], default_country_code, strict=True)
            if not number:
                country_code = rec.country_id and rec.country_id.code or default_country_code
                number = convert_phone_number(rec[number_field], country_code)
            # Ne rien faire si le numéro est déjà présent
            if rec.of_phone_number_ids.filtered(lambda p: p.number == number):
                continue
            else:
                # On remplace la valeur actuelle s'il y en a une
                current_phone = rec.of_phone_number_ids.filtered(lambda p: p.type == number_type)
                if current_phone:
                    rec.of_phone_number_ids = [(1, current_phone[0].id, {'number': number})]
                # Sinon on crée le nouveau numéro
                else:
                    rec.of_phone_number_ids = [(0, 0, {'number': number, 'type': number_type})]

    @api.multi
    def _inverse_phone(self):
        self._of_set_number('phone', '01_domicile')

    @api.multi
    def _inverse_mobile(self):
        self._of_set_number('mobile', '03_mobile')

    @api.multi
    def _inverse_fax(self):
        self._of_set_number('fax', '04_fax')

    @api.multi
    def _compute_of_phone_error(self):
        for partner in self:
            for phone in partner.of_phone_number_ids:
                if phone.number != convert_phone_number(phone.number, strict=True):
                    partner.of_phone_error = True
                    break
            else:
                partner.of_phone_error = False

    @api.model
    def _search_of_phone_error(self, operator, value):
        partners = self.env['of.res.partner.phone'].search([('is_valid', operator, not value)]).mapped('partner_id')
        return [('id', 'in', partners.ids)]

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
        parent_id = vals.get('parent_id', False)
        if parent_id and not vals.get('is_company', False):
            parent = self.browse(parent_id)
            vals.update(customer=parent.customer, supplier=parent.supplier)
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
        # Permet la synchronisation des champs customer et supplier pour tout les contacts liés
        if ('customer' in vals or 'supplier' in vals) and self._context.get('partner_recursion', True):
            for partner in self:
                parent = partner
                while parent.parent_id:
                    parent = parent.parent_id
                partners = self.search([('id', 'child_of', parent.id), ('is_company', '=', False)])
                values = {}
                if 'customer' in vals:
                    values['customer'] = vals['customer']
                if 'supplier' in vals:
                    values['supplier'] = vals['supplier']
                partners.with_context(partner_recursion=False).write(values)
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
    _rec_name = 'number'

    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire", index=True, ondelete='cascade')
    number = fields.Char(string="Numéro")
    number_display = fields.Char(
        string="Numéro au format national", compute="_compute_number_display", inverse="_inverse_number_display")
    type = fields.Selection(selection=PHONE_TYPES, string="Type de numéro", required=True)
    title_id = fields.Many2one(
        comodel_name="res.partner.title", string="Civilité du numéro", domain="[('of_used_for_phone', '=', True)]")
    is_valid = fields.Boolean(string="Est valide", compute='_compute_is_valid', store=True)

    @api.depends('number')
    def _compute_number_display(self):
        user_country_code = self.env.user.country_id.code or self.env.user.company_id.country_id.code or 'FR'
        for rec in self:
            if rec.is_valid:
                rec.number_display = convert_phone_number(rec.number, user_country_code, new_format='country')
            else:
                rec.number_display = rec.number

    @api.multi
    def _inverse_number_display(self):
        default_country_code = self.env.user.country_id.code or self.env.user.company_id.country_id.code or 'FR'
        for rec in self:
            number = convert_phone_number(rec.number_display, default_country_code, strict=True)
            if not number:
                country_code = rec.partner_id.country_id and rec.partner_id.country_id.code or default_country_code
                number = convert_phone_number(rec.number_display, country_code)
            rec.number = number

    @api.depends('number')
    def _compute_is_valid(self):
        for rec in self:
            rec.is_valid = bool(convert_phone_number(rec.number, strict=True))

    @api.onchange('number_display')
    def _onchange_number_display(self):
        default_country_code = self.env.user.country_id.code or self.env.user.company_id.country_id.code or 'FR'
        for rec in self:
            number = convert_phone_number(rec.number_display, default_country_code, strict=True)
            if not number:
                country_code = rec.partner_id.country_id and rec.partner_id.country_id.code or default_country_code
                number = convert_phone_number(rec.number_display, country_code)
            rec.number = number

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
                country_code = partner_id.country_id and partner_id.country_id.code or "FR"
                if phone:
                    number = convert_phone_number(phone, country_code)
                    phone_number_ids.append((0, 0, {'number': number, 'type': '01_domicile'}))
                if mobile:
                    number = convert_phone_number(mobile, country_code)
                    phone_number_ids.append((0, 0, {'number': number, 'type': '03_mobile'}))
                if fax:
                    number = convert_phone_number(fax, country_code)
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
                args = [(args[0][0], args[0][1], args[0][2][1:].replace(" ", ""))]

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
