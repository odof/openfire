# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import threading
import logging
from odoo import models, api, tools, fields, _
from odoo.exceptions import ValidationError
from odoo.modules import get_module_resource

_logger = logging.getLogger(__name__)

try:
    import phonenumbers
except ImportError:
    _logger.debug(u"Impossible d'importer la librairie Python 'phonenumbers'.")

PHONE_TYPES = [('01_domicile', "Home"),
               ('02_bureau', "Office"),
               ('03_mobile', "Mobile"),
               ('04_fax', "Fax")]


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

    name = fields.Char(tracking=True)
    street = fields.Char(tracking=True)
    street2 = fields.Char(tracking=True)
    zip = fields.Char(tracking=True)
    city = fields.Char(tracking=True)
    country_id = fields.Many2one(tracking=True)
    email = fields.Char(tracking=True)
    phone = fields.Char(compute='_compute_old_phone_fields', inverse='_inverse_phone')
    mobile = fields.Char(compute='_compute_old_phone_fields', inverse='_inverse_mobile')
    fax = fields.Char(compute='_compute_old_phone_fields', inverse='_inverse_fax')
    of_phone_number_ids = fields.One2many(
        comodel_name='of.res.partner.phone', inverse_name='partner_id', string="Phone numbers")
    of_phone_error = fields.Boolean(
        string="Badly formatted phone numbers", compute='_compute_of_phone_error', search='_search_of_phone_error')
    of_parent_category_id = fields.Many2many(
        comodel_name='res.partner.category', string="Parent labels", compute='_compute_parent_category')
    of_default_address = fields.Boolean(string="Default address")

    of_last_order_date = fields.Date(
        string="Last quote date", compute='_compute_of_last_order_date', compute_sudo=True)
    of_potential_duplication = fields.Boolean(
        string="Potential duplicate ?", compute='_compute_of_potential_duplication',
        search='_search_of_potential_duplication')

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
            if isinstance(partner.id, models.NewId):
                partner.of_parent_category_id = False
                continue

            partners = self.search([('id', 'parent_of', partner.id)])
            partners -= partner
            partner.of_parent_category_id = partners.mapped('category_id')

    def _compute_of_last_order_date(self):
        for partner in self:
            last_order = self.env['sale.order'].search([('partner_id', "=", partner.id)], order='id desc', limit=1)
            partner.of_last_order_date = last_order.date_order if last_order else False

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

            # On remplace la valeur actuelle s'il y en a une
            current_phone = rec.of_phone_number_ids.filtered(lambda p: p.type == number_type)
            if current_phone:
                rec.of_phone_number_ids = [(1, current_phone[0].id, {'number': number})]
            # Sinon on crée le nouveau numéro si la valeur est non vide
            elif number:
                rec.of_phone_number_ids = [(0, 0, {'number': number, 'type': number_type})]

    def _inverse_phone(self):
        for rec in self:
            if rec.of_phone_number_ids.filtered(lambda p: p.type == '01_domicile') or \
                    not rec.of_phone_number_ids.filtered(lambda p: p.type == '02_bureau'):
                rec._of_set_number('phone', '01_domicile')
            else:
                rec._of_set_number('phone', '02_bureau')

    def _inverse_mobile(self):
        self._of_set_number('mobile', '03_mobile')

    def _inverse_fax(self):
        self._of_set_number('fax', '04_fax')

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
        return super(ResPartner, self.with_context(of_show_address_line=True)).name_search(
            name=name, args=args, operator=operator, limit=limit)

    def name_get(self):
        """ Permet de renvoyer le nom + la ville du client quand valeur du contexte 'of_show_address_line' présent """
        name = self._rec_name
        if self._context.get('of_show_address_line') \
                and name in self._fields \
                and self.env['ir.config_parameter'].sudo().get_param('of.partner.display_city'):
            convert = self._fields[name].convert_to_display_name
            result = [(
                record.id,
                f"{convert(record[name], record)}{''.join([' (', record.city, ')']) if record.city else ''}"
            ) for record in self]

        elif self._context.get('show_email'):
            result = []
            for partner in self:
                name = partner.name or ''
                if partner.email:
                    name = f"{partner.email} <{name}>"
                result.append((partner.id, name))
        else:
            result = super().name_get()
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

        if not image:
            if partner_type == 'invoice':
                img_path = get_module_resource('base', 'static/src/img', 'money.png')
            elif partner_type == 'delivery':
                img_path = get_module_resource('base', 'static/src/img', 'truck.png')
            elif is_company:
                img_path = get_module_resource('base', 'static/src/img', 'company_image.png')
            else:
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
        if parent_id and isinstance(parent_id, int) and not values.get('ref') and \
                'default_ref' not in self._context:
            values['ref'] = self.browse(parent_id).ref
        return super()._add_missing_default_values(values)

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
                        raise ValidationError(
                            _("The customer account number is already in use and must be unique (%s).") % (ref,))
                else:
                    parent_id = id
            if not ids:
                break
            cr.execute("SELECT id,parent_id FROM res_partner WHERE id IN %s", (tuple(ids),))
        return True

    def _compute_of_potential_duplication(self):
        # On teste l'existence de doublons potentiels basés sur l'email ou les numéros de téléphone
        self = self.sudo()
        for partner in self:
            partner.of_potential_duplication = bool(partner.check_duplications())

    @api.model
    def _search_of_potential_duplication(self, operator, value):
        if operator == '=' and value:
            self._cr.execute(
                "   SELECT    DISTINCT RP.id"
                "   FROM      res_partner RP"
                "   WHERE     EXISTS      (   SELECT  1"
                "                             FROM    res_partner RP2"
                "                             WHERE   RP2.id      != RP.id"
                "                             AND     RP2.email   = RP.email"
                "                         )")
            same_email_ids = [x[0] for x in self._cr.fetchall()]
            self._cr.execute(
                "   SELECT    DISTINCT ORPP.partner_id"
                "   FROM      of_res_partner_phone      ORPP"
                "   WHERE     EXISTS                    (   SELECT  1"
                "                                           FROM    of_res_partner_phone    ORPP2"
                "                                           WHERE   ORPP2.partner_id        != ORPP.partner_id"
                "                                           AND     ORPP2.number            = ORPP.number"
                "                                       )")
            same_phone_ids = [x[0] for x in self._cr.fetchall()]
            return [('id', 'in', same_email_ids + same_phone_ids)]

    def check_duplications(self):
        self.ensure_one()
        # On teste l'existence de doublons potentiels basés sur l'email ou les numéros de téléphone
        self = self.sudo()
        same_email_ids = self.env['res.partner']
        if self.email:
            same_email_ids = self.search([('email', '=', self.email), ('id', '!=', self.id)])
        same_phone_ids = self.env['res.partner']
        if self.of_phone_number_ids:
            numbers_list = self.of_phone_number_ids.mapped('number')
            same_phone_ids = self.env['of.res.partner.phone'].\
                search([('number', 'in', numbers_list), ('partner_id', '!=', self.id)]).mapped('partner_id')
        duplication_ids = same_email_ids | same_phone_ids
        return duplication_ids.ids if duplication_ids else False

    @api.model_create_multi
    def create(self, vals_list):
        partner = super().create(vals_list)
        for vals in vals_list:
            self._check_no_ref_duplicate(vals.get('ref'))
        # Calcul de la ref en fonction de la configuration
        if partner.company_id.of_ref_mode == 'id' and not partner.ref:
            if self.env['res.partner'].with_context(active_test=False).search([('ref', '=', str(partner.id))]):
                i = 2
                while self.env['res.partner'].with_context(active_test=False).search(
                        [('ref', '=', f'{str(partner.id)}-{i}')]):
                    i += 1
                partner.ref = f'{str(partner.id)}-{i}'
            else:
                partner.ref = str(partner.id)
        return partner

    @api.model
    def _update_refs(self, new_ref, partner_refs):
        # Avant de mettre a jour les enfants, on vérifie que les partenaires avec cette référence ont bien tous
        # un parent commun
        self._check_no_ref_duplicate(new_ref)

        to_update_ids = []
        while partner_refs:
            partner, old_ref = partner_refs.pop()
            for child in partner.child_ids:
                if child.ref == old_ref:
                    # La reference du contact était la même que celle du parent, on met à jour et on continue
                    # le parcours
                    to_update_ids.append(child.id)
                    partner_refs.append((child, old_ref))
        if to_update_ids:
            self.env['res.partner'].browse(to_update_ids).write({'ref': new_ref})
        return True

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
        res = super().write(vals)
        if write_ref:
            self._update_refs(ref, partner_refs)
        # Calcul de la ref en fonction de la configuration
        for partner in self.filtered(lambda p: p.company_id.sudo().of_ref_mode == 'id' and not p.ref):
            if not self.env['res.partner'].with_context(active_test=False).search([('ref', '=', str(partner.id))]):
                partner.ref = str(partner.id)
            else:
                i = 2
                while self.env['res.partner'].with_context(active_test=False).search([
                        ('ref', '=', f'{str(partner.id)}-{i}')]):
                    i += 1
                partner.ref = f'{str(partner.id)}-{i}'
        return res

    # Permet à l'auteur du mail de le recevoir en copie.
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
        return super()._notify(message, force_send, send_after_commit, user_signature)
