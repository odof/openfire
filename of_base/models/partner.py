# -*- coding: utf-8 -*-

import threading
import logging

from odoo import models, api, tools, fields
from odoo.exceptions import ValidationError
from odoo.modules import get_module_resource
from odoo.addons.base_iban.models.res_partner_bank import validate_iban

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
        """
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        """
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
                ('notify_email', '!=', 'none')])._notify_by_email(message, force_send=force_send,
                                                                  send_after_commit=send_after_commit,
                                                                  user_signature=user_signature)
        return super(ResPartner, self)._notify(message, force_send, send_after_commit, user_signature)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model_cr_context
    def _auto_init(self):
        # A l'installation du module il faut déterminer si le type des comptes bancaires existants
        cr = self._cr
        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name = 'res_partner_bank' AND column_name = 'acc_type'")
        acc_type_exists = bool(cr.fetchall())
        res = super(ResPartnerBank, self)._auto_init()

        if not acc_type_exists:
            # Initialisation des comptes bancaires existants
            cr.execute("SELECT id, acc_number FROM res_partner_bank")
            for acc_id, acc_number in cr.fetchall():
                try:
                    validate_iban(acc_number)
                except ValidationError:
                    cr.execute("UPDATE res_partner_bank SET acc_type = 'bank' WHERE id = %s", (acc_id, ))
        return res

    acc_type = fields.Selection(
        [('bank', u"Banque"), ('iban', u"IBAN")],
        string=u"Type de compte", required=True, default='iban',
        help=u"Laissez le type de compte IBAN pour laisser le logiciel vérifier la validité du code saisi.\n"
             u"Utilisez le type Banque pour tout autre type de compte, aucune vérification ne sera effectuée."
    )

    @api.multi
    def write(self, vals):
        if (vals.get('acc_type') == 'iban') and 'acc_number' not in vals:
            for bank in self:
                # On ajoute acc_number dans vals pour forcer son nettoyage dans le module base_iban
                vals['acc_number'] = bank.acc_number
                super(ResPartnerBank, bank).write(vals)
        else:
            return super(ResPartnerBank, self).write(vals)
        return True


class ResPartnerTitle(models.Model):
    _inherit = 'res.partner.title'

    of_used_for_phone = fields.Boolean(string="Utilisée pour les numéros de téléphone", default=True)


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
