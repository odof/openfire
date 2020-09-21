# -*- encoding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, timedelta, date
import pytz, math, json, urllib, requests
from math import cos
from odoo.addons.of_planning_tournee.models.of_planning_tournee import distance_points
from odoo.addons.of_geolocalize.models.of_geo import GEO_PRECISION
from odoo.tools import config
from odoo.exceptions import UserError

SEARCH_MODES = [
    ('distance', u'Distance (km)'),
    ('duree', u'Durée (min)'),
]


@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

def hours_to_strs(*hours):
    """ Convertit une liste d'heures sous forme de floats en liste de str de type '00h00'
    """
    return tuple("%02dh%02d" % (hour, round((hour % 1) * 60)) for hour in hours)

class OFRDVCommercial(models.TransientModel):
    _name = 'of.rdv.commercial'
    _description = u'Prise de RDV commercial'

    @api.model
    def _default_partner(self):
        active_model = self._context.get('active_model', '')
        partner_id = False
        if active_model == "res.partner":
            partner_id = self._context['active_ids'][0]
        elif active_model == "crm.lead":
            lead_id = self._context['active_ids'][0]
            lead = self.env["crm.lead"].browse(lead_id)
            partner_id = lead.partner_id.id

        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            while partner.parent_id:
                partner = partner.parent_id
            return partner
        return False

    @api.model
    def _default_lead(self):
        active_model = self._context.get('active_model', '')
        lead = False
        if active_model == "crm.lead":
            lead_id = self._context['active_ids'][0]
            lead = self.env["crm.lead"].browse(lead_id)
        return lead

    @api.model
    def _default_user(self):
        active_model = self._context.get('active_model', '')
        if active_model == "crm.lead":
            lead_id = self._context['active_ids'][0]
            lead = self.env["crm.lead"].browse(lead_id)
            commercial = lead.user_id
            if self.env.user.company_id.id not in commercial.sudo().company_ids._ids:
                return False
            return commercial
        elif active_model == "res.partner":
            partner_id = self._context['active_ids'][0]
            partner = self.env['res.partner'].browse(partner_id)
            while partner.parent_id and not partner.user_id:
                partner = partner.parent_id
            commercial = partner.user_id
            if self.env.user.company_id.id not in commercial.sudo().company_ids._ids:
                return False
            return commercial
        else:
            return False

    @api.model
    def _default_employee(self):
        user_id = self._default_user()
        if user_id and len(user_id.employee_ids) > 0:
            return user_id.employee_ids[0]
        else:
            return False

    @api.model
    def _default_address(self):  # a verif
        partner_obj = self.env['res.partner']
        active_model = self._context.get('active_model', '')
        if active_model == "crm.lead":
            lead_id = self._context['active_ids'][0]
            lead = self.env["crm.lead"].browse(lead_id)
            address_id = lead.partner_id.id
        elif active_model == "res.partner":
            partner = partner_obj.browse(self._context['active_ids'][0])
            address_id = partner.address_get(['delivery'])['delivery']
        else:
            address_id = False

        if address_id:
            address = partner_obj.browse(address_id)
            if not (address.geo_lat or address.geo_lng):
                address = partner_obj.search(['|', ('id', '=', address.id), ('parent_id', '=', address.id),
                                              '|', ('geo_lat', '!=', 0), ('geo_lng', '!=', 0)], limit=1)
                if not address:
                    address = partner_obj.search(['|', ('id', '=', address_id), ('parent_id', '=', address_id)], limit=1)
            return address
        return False

    def _get_default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    name = fields.Char(string=u'Libellé', size=64, required=False, default="Planifier RDVcom")
    description = fields.Html(string='Description')
    user_id = fields.Many2one('res.users', string=u"Compte Commercial", required=True, default=_default_user)
    employee_id = fields.Many2one(
        'hr.employee', string=u"Commercial", required=True, default=_default_employee,
        domain=lambda self: [('user_id.company_ids', 'child_of', self.env.user.company_id.id)],
        help=u"La liste des employés proposés est constituée des employés qui ont accès à la société courante")
    duree = fields.Float(string=u'Durée du RDV', required=True, digits=(12, 2), default=1)
    creneau_ids = fields.One2many('of.rdv.commercial.line', 'wizard_id', string='Proposition de RDVs')
    date_propos = fields.Datetime(string=u'RDV Début')
    date_propos_hour = fields.Float(string=u'Heure de début', digits=(12, 5))
    date_recherche_debut = fields.Date(
        string=u'À partir du', required=True,
        default=lambda *a: (date.today() + timedelta(days=1)).strftime('%Y-%m-%d'))
    date_recherche_fin = fields.Date(
        string=u"Jusqu'au", required=True, default=lambda *a: (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'))
    partner_id = fields.Many2one('res.partner', string='Client', required=True, readonly=True, default=_default_partner)
    partner_name = fields.Char(related='partner_id.name')
    partner_child_ids = fields.One2many(related="partner_id.child_ids", readonly=True)  # pour domain dans XML
    partner_address_id = fields.Many2one('res.partner', string="Adresse du RDV", default=_default_address,
                                         domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]")
    date_display = fields.Char(string='Jour du RDV', size=64, readonly=True)
    lead_id = fields.Many2one(
        'crm.lead', string='Opportunité', default=_default_lead, domain="[('partner_id', '=', partner_id)]")
    mode_recherche = fields.Selection(SEARCH_MODES, string="Mode de recherche", required=True, default="distance")
    max_recherche = fields.Float(string="Maximum", digits=(12, 0))
    allday = fields.Boolean('All Day', default=False)
    hor_md = fields.Float(string=u'Matin début', required=True, digits=(12, 1), default=9)
    hor_mf = fields.Float(string='Matin fin', required=True, digits=(12, 1), default=12)
    hor_ad = fields.Float(string=u'Après-midi début', required=True, digits=(12, 1), default=14)
    hor_af = fields.Float(string=u'Après-midi fin', required=True, digits=(12, 1), default=18)
    jour_ids = fields.Many2many(
        'of.jours', 'rdvcom_jours', 'rdvcom_id', 'jour_id', string='Jours travaillés', required=True,
        default=_get_default_jours)
    tz = fields.Selection(
        _tz_get, string='Fuseau horaire', default=lambda self: self.env.user.tz or 'Europe/Paris', required=True,
        help="The Team's timezone, used to output proper date and time values "
             "inside printed reports. It is important to set a value for this field. "
             "You should use the same timezone that is otherwise used to pick and "
             "render date and time values: your computer's timezone.")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset')

    zero_result = fields.Boolean(string="Recherche infructueuse", default=False, help="Aucun résultat")
    zero_dispo = fields.Boolean(string="Recherche infructueuse", default=False, help="Aucun résultat sufisament proche")
    display_search = fields.Boolean(string=u"Voir critères de recherche", default=True)
    display_res = fields.Boolean(string=u"Voir Résultats", default=False)
    display_horaires = fields.Boolean(string="Voir horaires", default=False)
    res_line_id = fields.Many2one("of.rdv.commercial.line", string="Créneau Sélectionné")

    lieu = fields.Selection([
        ("customer", "Chez le client"),
        ("phone", "Au téléphone"),
        ("company", "Dans les locaux"),
        ("other", "Autre")
        ], string="Lieu du RDV", required=True, default="customer")

    lieu_company_id = fields.Many2one("res.company", string="(précisez)")
    lieu_rdv_id = fields.Many2one("res.partner", string="(précisez)")
    lieu_address_street = fields.Char(string="Rue", compute="_compute_address")
    lieu_address_street2 = fields.Char(string="Rue (2)", compute="_compute_address")
    lieu_address_city = fields.Char(string="Ville", compute="_compute_address")
    lieu_address_state_id = fields.Many2one("res.country.state", string=u"Région", compute="_compute_address")
    lieu_address_zip = fields.Char(string="Code postal", compute="_compute_address")
    lieu_address_country_id = fields.Many2one("res.country", string="Pays", compute="_compute_address")

    # champs ajoutés pour la vue map
    geo_lat = fields.Float(
        string='Geo Lat', digits=(8, 8), group_operator=False, help="latitude field", compute="_compute_address",
        search='_search_lat')
    geo_lng = fields.Float(
        string='Geo Lng', digits=(8, 8), group_operator=False, help="longitude field", compute="_compute_address",
        search='_search_lng')
    precision = fields.Selection(
        GEO_PRECISION, default='not_tried', compute="_compute_address", search='_search_precision',
        help=u"Niveau de précision de la géolocalisation.\n"
             u"bas: à la ville.\n"
             u"moyen: au village\n"
             u"haut: à la rue / au voisinage\n"
             u"très haut: au numéro de rue\n")
    ignorer_geo = fields.Boolean(u"Ignorer données géographiques")
    geocode_retry = fields.Boolean("Geocodage retenté")

    of_color_ft = fields.Char(string="Couleur de texte", compute="_compute_colors")
    of_color_bg = fields.Char(string="Couleur de fond", compute="_compute_colors")

    def _search_lat(self, operator, operand):
        partners_customer = self.env['res.partner']
        companies = self.env['res.company']
        partners_other = self.env['res.partner']
        for wizard in self:
            if wizard.lieu == "customer":
                partners_customer |= wizard.partner_address_id
            elif wizard.lieu == "company":
                companies |= wizard.lieu_company_id
            elif wizard.lieu == "other":
                partners_other |= wizard.lieu_rdv_id
            else:
                continue
        partners_customer = partners_customer.search([('id', 'in', partners_customer._ids), ('geo_lat', operator, operand)])
        partners_other = partners_other.search([('id', 'in', partners_other._ids), ('geo_lat', operator, operand)])
        companies = companies.search([('id', 'in', companies._ids), ('partner_id.geo_lat', operator, operand)])
        return [('id', 'in', self.env['of.rdv.commercial'].search(['|', '&', ('lieu_company_id', 'in', companies._ids),
                                                                             ('lieu', '=', 'company'),
                                                                        '|', '&', ('partner_address_id', 'in', partners_customer._ids),
                                                                                  ('lieu', '=', 'customer'),
                                                                             '&', ('lieu_rdv_id', 'in', partners_other._ids),
                                                                                  ('lieu', '=', 'other')])._ids)]

    def _search_lng(self, operator, operand):
        partners_customer = self.env['res.partner']
        companies = self.env['res.company']
        partners_other = self.env['res.partner']
        for wizard in self:
            if wizard.lieu == "customer":
                partners_customer |= wizard.partner_address_id
            elif wizard.lieu == "company":
                companies |= wizard.lieu_company_id
            elif wizard.lieu == "other":
                partners_other |= wizard.lieu_rdv_id
            else:
                continue
        partners_customer = partners_customer.search([('id', 'in', partners_customer._ids), ('geo_lng', operator, operand)])
        partners_other = partners_other.search([('id', 'in', partners_other._ids), ('geo_lng', operator, operand)])
        companies = companies.search([('id', 'in', companies._ids), ('partner_id.geo_lng', operator, operand)])
        return [('id', 'in', self.env['of.rdv.commercial'].search(['|', '&', ('lieu_company_id', 'in', companies._ids),
                                                                             ('lieu', '=', 'company'),
                                                                        '|', '&', ('partner_address_id', 'in', partners_customer._ids),
                                                                                  ('lieu', '=', 'customer'),
                                                                             '&', ('lieu_rdv_id', 'in', partners_other._ids),
                                                                                  ('lieu', '=', 'other')])._ids)]

    def _search_precision(self, operator, operand):
        partners_customer = self.env['res.partner']
        companies = self.env['res.company']
        partners_other = self.env['res.partner']
        for wizard in self:
            if wizard.lieu == "customer":
                partners_customer |= wizard.partner_address_id
            elif wizard.lieu == "company":
                companies |= wizard.lieu_company_id
            elif wizard.lieu == "other":
                partners_other |= wizard.lieu_rdv_id
            else:
                continue
        partners_customer = partners_customer.search([('id', 'in', partners_customer._ids), ('precision', operator, operand)])
        partners_other = partners_other.search([('id', 'in', partners_other._ids), ('precision', operator, operand)])
        companies = companies.search([('id', 'in', companies._ids), ('partner_id.precision', operator, operand)])
        return [('id', 'in', self.env['of.rdv.commercial'].search(['|', '&', ('lieu_company_id', 'in', companies._ids),
                                                                             ('lieu', '=', 'company'),
                                                                        '|', '&', ('partner_address_id', 'in', partners_customer._ids),
                                                                                  ('lieu', '=', 'customer'),
                                                                             '&', ('lieu_rdv_id', 'in', partners_other._ids),
                                                                                  ('lieu', '=', 'other')])._ids)]

    @api.multi
    @api.depends("lieu", "partner_address_id", "lieu_company_id", "lieu_rdv_id")
    def _compute_address(self):
        for wizard in self:
            if wizard.lieu == "customer":
                values = {
                    "lieu_address_street": wizard.partner_address_id.street,
                    "lieu_address_street2": wizard.partner_address_id.street2,
                    "lieu_address_city": wizard.partner_address_id.city,
                    "lieu_address_state_id": wizard.partner_address_id.state_id.id,
                    "lieu_address_zip": wizard.partner_address_id.zip,
                    "lieu_address_country_id": wizard.partner_address_id.country_id.id,
                    "geo_lat": wizard.partner_address_id.geo_lat,
                    "geo_lng": wizard.partner_address_id.geo_lng,
                    "precision": wizard.partner_address_id.precision,
                }
            elif wizard.lieu == "company":
                values = {
                    "lieu_address_street": wizard.lieu_company_id.partner_id.street,
                    "lieu_address_street2": wizard.lieu_company_id.partner_id.street2,
                    "lieu_address_city": wizard.lieu_company_id.partner_id.city,
                    "lieu_address_state_id": wizard.lieu_company_id.partner_id.state_id.id,
                    "lieu_address_zip": wizard.lieu_company_id.partner_id.zip,
                    "lieu_address_country_id": wizard.lieu_company_id.partner_id.country_id.id,
                    "geo_lat": wizard.lieu_company_id.partner_id.geo_lat,
                    "geo_lng": wizard.lieu_company_id.partner_id.geo_lng,
                    "precision": wizard.lieu_company_id.partner_id.precision,
                }
            elif wizard.lieu == "other":
                values = {
                    "lieu_address_street": wizard.lieu_rdv_id.street,
                    "lieu_address_street2": wizard.lieu_rdv_id.street2,
                    "lieu_address_city": wizard.lieu_rdv_id.city,
                    "lieu_address_state_id": wizard.lieu_rdv_id.state_id.id,
                    "lieu_address_zip": wizard.lieu_rdv_id.zip,
                    "lieu_address_country_id": wizard.lieu_rdv_id.country_id.id,
                    "geo_lat": wizard.lieu_rdv_id.geo_lat,
                    "geo_lng": wizard.lieu_rdv_id.geo_lng,
                    "precision": wizard.lieu_rdv_id.precision,
                }
            else:
                values = {
                    "lieu_address_street": False,
                    "lieu_address_street2": False,
                    "lieu_address_city": False,
                    "lieu_address_state_id": False,
                    "lieu_address_zip": False,
                    "lieu_address_country_id": False,
                    "geo_lat": False,
                    "geo_lng": False,
                    "precision": "no_address",
                }
            wizard.update(values)

    @api.depends('tz')
    def _compute_tz_offset(self):
        for wizard in self:
            wizard.tz_offset = datetime.now(pytz.timezone(wizard.tz or 'GMT')).strftime('%z')

    @api.depends("user_id")
    def _compute_colors(self):
        for wizard in self:
            if wizard.user_id:
                wizard.of_color_ft = wizard.user_id.of_color_ft
                wizard.of_color_bg = wizard.user_id.of_color_bg
            else:
                wizard.of_color_ft = "#0D0D0D"
                wizard.of_color_bg = "#F0F0F0"

    @api.onchange('partner_address_id', 'lieu_rdv_id', 'lieu_company_id')
    def _onchange_adresse_rdv(self):
        """réinitialise geocode_retry sur changement d'adresse du rdv"""
        self.ensure_one()
        self.geocode_retry = False

    @api.onchange('lieu')
    def _onchange_lieu(self):
        self.ensure_one()
        if not self.lieu:
            return
        if self.lieu == "phone":
            self.ignorer_geo = True
            self.lieu_rdv_id = False
            self.lieu_company_id = False
        elif self.lieu == "company":
            self.ignorer_geo = False
            self.lieu_company_id = self.user_id.company_id.id
            self.lieu_rdv_id = self.user_id.company_id.partner_id.id
        elif self.lieu == "customer":
            self.ignorer_geo = False
            self.lieu_company_id = False
            self.lieu_rdv_id = self.partner_address_id.id
        else:  # other
            self.lieu_company_id = False
            self.ignorer_geo = False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Met a jour les horaires de travail, adresses de départ et d'arrivée"""
        self.ensure_one()
        if self.employee_id:
            if self.employee_id.user_id:
                vals = {
                    "hor_md": self.employee_id.of_hor_md,
                    "hor_mf": self.employee_id.of_hor_mf,
                    "hor_ad": self.employee_id.of_hor_ad,
                    "hor_af": self.employee_id.of_hor_af,
                    "tz": self.employee_id.of_tz or "Europe/Paris",
                    "jour_ids": [(5, 0, 0)] + [(4, le_id, False) for le_id in self.employee_id.of_jour_ids._ids],
                    "user_id": self.employee_id.user_id,
                    }
                self.update(vals)
                if not self.jour_ids:
                    raise UserError(u"Cet employé n'a aucun jour dans sa liste des jours travaillés. \nVous pouvez configurer ses jours travaillés dans sa fiche employé.")
            else:
                raise UserError(u"Cet employé n'est pas rattaché à un compte utilisateur. \nPour le rattacher à un compte utilisateur rendez-vous sur sa fiche employé, onglet 'paramètre RH', champ 'utilisateur lié'.")

    @api.onchange('mode_recherche')
    def _onchange_mode_recherche(self):
        self.ensure_one()
        if self.mode_recherche and self.mode_recherche == u"distance":
            self.max_recherche = 50
        elif self.mode_recherche:
            self.max_recherche = 60

    @api.onchange('date_recherche_debut')
    def _onchange_date_recherche_debut(self):
        self.ensure_one()
        if self.date_recherche_debut:
            d_drd = fields.Date.from_string(self.date_recherche_debut)
            d_drf = d_drd + timedelta(days=6)
            self.date_recherche_fin = fields.Date.to_string(d_drf)

    @api.onchange('date_recherche_fin')
    def _onchange_date_recherche_fin(self):
        self.ensure_one()
        if self.date_recherche_fin and self.date_recherche_fin < self.date_recherche_debut:
            raise UserError(u"La date de fin de recherche doit être postérieure à la date de début de recherche")

    @api.onchange('hor_md')
    def _onchange_hor_md(self):
        self.ensure_one()
        if self.hor_md and self.hor_mf and self.hor_md > self.hor_mf:
            raise UserError(u"L'Heure de début de matinée doit être antérieure à l'heure de fin de matinée")
        if self.hor_md and self.hor_md < 0:
            raise UserError(u"L'Heure de début de matinée doit être supérieure à 0")

    @api.onchange('hor_mf')
    def _onchange_hor_mf(self):
        self.ensure_one()
        if self.hor_md and self.hor_mf and self.hor_md > self.hor_mf:
            raise UserError(u"L'Heure de début de matinée doit être antérieure à l'heure de fin de matinée")
        elif self.hor_mf and self.hor_ad and self.hor_mf > self.hor_ad:
            raise UserError(u"L'Heure de fin de matinée doit être antérieure à l'heure de début d'après-midi")

    @api.onchange('hor_ad')
    def _onchange_hor_ad(self):
        self.ensure_one()
        if self.hor_ad and self.hor_af and self.hor_ad > self.hor_af:
            raise UserError(u"L'Heure de début d'après-midi doit être antérieure à l'heure de fin d'après-midi")
        elif self.hor_mf and self.hor_ad and self.hor_mf > self.hor_ad:
            raise UserError(u"L'Heure de fin de matinée doit être antérieure à l'heure de début d'après-midi")

    @api.onchange('hor_af')
    def _onchange_hor_af(self):
        self.ensure_one()
        if self.hor_ad and self.hor_af and self.hor_ad > self.hor_af:
            raise UserError(u"L'Heure de début d'après-midi doit être antérieure à l'heure de fin d'après-midi")
        if self.hor_af and self.hor_af > 24:
            raise UserError(u"L'Heure de fin d'après-midi doit être inférieure ou égale à 24")

    @api.multi
    def _check_horaires(self):
        self.ensure_one()
        return 0 <= self.hor_md <= self.hor_mf <= self.hor_ad <= self.hor_af <= 24

    @api.multi
    def toggle_horaires(self):
        """Affiche / cache les horaires pour pouvoir les modifier"""
        self.ensure_one()
        self.display_horaires = not self.display_horaires

        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_geocode(self):
        self.ensure_one()
        if self.geocode_retry:
            raise UserError("Votre géocodeur par défaut n'a pas réussi a géocoder cette adresse")
        if self.lieu == 'customer':
            self.partner_address_id.geo_code()
        elif self.lieu == 'company':
            self.lieu_company_id.partner_id.geo_code()
        else:
            self.lieu_rdv_id.geo_code()
        self.geocode_retry = True
        if self.geo_lat != 0 or self.geo_lng != 0:
            self.ignorer_geo = False
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def button_calcul(self):
        # Calcule a prochaine intervention à partir du lendemain de la date courante
        if not self.employee_id.user_id:
            raise UserError(u"Cet employé n'est pas rattaché à un compte utilisateur. \nPour le rattacher à un compte utilisateur rendez-vous sur sa fiche employé, onglet 'paramètre RH', champ 'utilisateur lié'.")
        self.compute()
        context = dict(self._context)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.rdv.commercial',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': context,
        }

    def create_creneau(self, event_deb, event_fin, tz, date_recherche_da, date_recherche_str, event=False):
        """
        Permet la création de créneau dans le wizard
        :param event_deb: Heure de début
        :param event_fin: Heure de fin
        :param tz: Timezone
        :param date_recherche_da: Date de recherche (datetime)
        :param date_recherche_str: Date de recherche (str)
        :param event: RDV déjà existant
        """
        wizard_line_obj = self.env['of.rdv.commercial.line']
        description = "%s-%s" % tuple(hours_to_strs(event_deb, event_fin))

        date_debut_dt = datetime.combine(date_recherche_da, datetime.min.time()) + timedelta(hours=event_deb)
        date_debut_dt = tz.localize(date_debut_dt, is_dst=None).astimezone(pytz.utc)
        date_fin_dt = datetime.combine(date_recherche_da, datetime.min.time()) + timedelta(hours=event_fin)
        date_fin_dt = tz.localize(date_fin_dt, is_dst=None).astimezone(pytz.utc)

        wizard_line_obj.create({
            'debut_dt': date_debut_dt,
            'fin_dt': date_fin_dt,
            'date_flo': event_deb,
            'date_flo_deadline': event_fin,
            'date': date_recherche_str,
            'description': description,
            'wizard_id': self.id,
            'user_id': self.user_id.id,
            'employee_id': self.employee_id.id,
            'user_partner_id': self.user_id.partner_id.id,
            'calendar_id': event and event.id,
            'categ_ids': event and [(4, le_id, False) for le_id in event.categ_ids._ids],
            'partner_ids': event and [(4, le_id, False) for le_id in event.partner_ids._ids],
            'name': event and event.name,
            'disponible': False if event else True,
            'ignorer_geo': self.ignorer_geo,
            'on_phone': event.of_lieu and event.of_lieu == 'phone' if event else self.lieu and self.lieu == 'phone',
            })

    @api.multi
    def compute(self):
        u"""Calcul des prochains créneaux disponibles
        NOTE : Si un service est sélectionné incluant le samedi et/ou le dimanche,
               ceux-cis seront traités comme des jours normaux du point de vue des équipes
        """
        # TODO: finir de commenter
        self.ensure_one()

        if not self._check_horaires():
            raise UserError(u"Vérifier les horaires de recherche")

        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])

        wizard_line_obj = self.env['of.rdv.commercial.line']
        calendar_obj = self.env['calendar.event']

        jours = [jour.numero for jour in self.jour_ids] if self.jour_ids else range(1, 6)

        # Suppression des anciens créneaux
        self.creneau_ids.unlink()

        un_jour = timedelta(days=1)

        d_avant_recherche = fields.Date.from_string(self.date_recherche_debut) - un_jour
        avant_recherche = fields.Date.to_string(d_avant_recherche)
        avant_recherche_debut_dt = tz.localize(datetime.strptime(avant_recherche+" 00:00:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        avant_recherche_fin_dt = tz.localize(datetime.strptime(avant_recherche+" 23:59:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        d_apres_recherche = fields.Date.from_string(self.date_recherche_fin) + un_jour
        apres_recherche = fields.Date.to_string(d_apres_recherche)
        apres_recherche_debut_dt = tz.localize(datetime.strptime(apres_recherche+" 00:00:00", "%Y-%m-%d %H:%M:%S"))  # local datetime
        apres_recherche_fin_dt = tz.localize(datetime.strptime(apres_recherche+" 23:59:00", "%Y-%m-%d %H:%M:%S"))  # local datetime

        # Création des créneaux de début et fin de recherche
        wizard_line_obj.create({
            'name': 'Début de la recherche',
            'debut_dt': avant_recherche_debut_dt,
            'fin_dt': avant_recherche_fin_dt,
            'date_flo': 0.0,
            'date_flo_deadline': 23.9,
            'date': d_avant_recherche,
            'wizard_id': self.id,
            'user_id': self.user_id.id,
            'employee_id': self.employee_id.id,
            'user_partner_id': self.user_id.partner_id.id,
            'calendar_id': False,
            'disponible': False,
            'allday': True,
            'virtuel': True,
            'ignorer_geo': self.ignorer_geo,
        })
        wizard_line_obj.create({
            'name': 'Fin de la recherche',
            'debut_dt': apres_recherche_debut_dt,
            'fin_dt': apres_recherche_fin_dt,
            'date_flo': 0.0,
            'date_flo_deadline': 23.9,
            'date': d_apres_recherche,
            'wizard_id': self.id,
            'user_id': self.user_id.id,
            'employee_id': self.employee_id.id,
            'user_partner_id': self.user_id.partner_id.id,
            'calendar_id': False,
            'disponible': False,
            'allday': True,
            'virtuel': True,
            'ignorer_geo': self.ignorer_geo,
        })

        date_recherche_da = d_avant_recherche
        u"""
        Parcours tous les jours inclus entre la date de début de recherche et la date de fin de recherche.
        Prends en compte les équipes qui peuvent effectuer la tache, et qui sont disponibles
        Ne prends pas en compte les jours non travaillés @TODO: passer les jours travaillés en many2many vers of.jour (module of_utils)
        """
        while date_recherche_da < d_apres_recherche:
            date_recherche_da += un_jour
            num_jour = date_recherche_da.isoweekday()

            # Restriction aux jours spécifiés dans le service
            while num_jour not in jours:
                date_recherche_da += un_jour
                num_jour = (num_jour + 1) % 7
            # Arreter la recherche si on dépasse la date de fin
            if date_recherche_da >= d_apres_recherche:
                break
            date_recherche_str = fields.Date.to_string(date_recherche_da)

            # Recherche de creneaux pour la date voulue et les équipes sélectionnées
            jour_deb_dt = tz.localize(datetime.strptime(date_recherche_str+" 00:00:00", "%Y-%m-%d %H:%M:%S"))
            jour_fin_dt = tz.localize(datetime.strptime(date_recherche_str+" 23:59:00", "%Y-%m-%d %H:%M:%S"))
            # Récupération des évenements déjà planifiées
            events = calendar_obj.search([
                                        ('start_datetime', '<=', date_recherche_str),
                                        ('stop_datetime', '>=', date_recherche_str),
                                        # ('start_date', '=', date_recherche_str)
                                        ], order='start_date')
            events = events.filtered(lambda e: self.user_id.partner_id in e.partner_ids or self.partner_id in e.partner_ids)

            event_dates_all = []
            for event in events:
                event_dates = [event]
                for event_date in (event.start_datetime, event.stop_datetime):
                    # Conversion des dates de début et de fin en nombres flottants et à l'heure locale
                    event_local_dt = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(event_date))

                    # Comme on n'affiche que les heures, il faut s'assurer de rester dans le bon jour
                    #   (pour les interventions étalées sur plusieurs jours)
                    event_local_dt = max(event_local_dt, jour_deb_dt)
                    event_local_dt = min(event_local_dt, jour_fin_dt)
                    date_event_locale_flo = round(event_local_dt.hour +
                                               event_local_dt.minute / 60.0 +
                                               event_local_dt.second / 3600.0, 5)
                    event_dates.append(date_event_locale_flo)
                self.create_creneau(event_dates[1], event_dates[2], tz, date_recherche_da, date_recherche_str, event=event_dates[0])
                event_dates_all.append(event_dates)

            deb = self.hor_md
            fin = self.hor_mf
            ad = self.hor_ad
            # TODO: possibilité intervention chevauchant la nuit
            for event, event_deb, event_fin in event_dates_all + [(False, 24, 24)]:
                if deb < event_deb and deb < fin:
                    # Un trou dans le planning, suffisant pour un créneau?
                    if deb < ad <= event_deb:
                        # On passe du matin à l'après-midi
                        # On vérifie la durée cumulée de la matinée et de l'après-midi car une intervention peut
                        # commencer avant la pause repas
                        event_deb = min(event_deb, self.hor_af)
                        duree = self.hor_mf - deb + event_deb - ad
                        if duree >= self.duree:
                            self.create_creneau(deb, fin, tz, date_recherche_da, date_recherche_str)
                            if ad < event_deb:
                                self.create_creneau(ad, event_deb, tz, date_recherche_da, date_recherche_str)
                        fin = self.hor_af
                    else:
                        duree = min(event_deb, fin) - deb
                        if duree >= self.duree:
                            self.create_creneau(deb, deb + duree, tz, date_recherche_da, date_recherche_str)

                if event_fin >= fin and fin <= ad:
                    deb = max(event_fin, ad)
                    fin = self.hor_af
                elif event_fin > deb:
                    deb = event_fin

        # Calcul des durées et distances
        date_debut_da = d_avant_recherche + un_jour
        date_fin_da = apres_recherche_da - un_jour
        if not self.ignorer_geo:
            wizard_line_obj.calc_distances_dates(date_debut_da, date_fin_da, self.id)

        nb, nb_dispo, first_res = wizard_line_obj.get_nb_dispo(self)

        vals = {}
        # Sélection du résultat
        if nb > 0:
            if self.lieu == 'company':
                address = self.lieu_company_id
            elif self.lieu == 'other':
                address = self.lieu_rdv_id
            else:
                address = self.partner_address_id
            name = address.name or (address.parent_id and address.parent_id.name) or ''
            if self.lieu == 'phone':
                name += u' (téléphonique)'
            else:
                name += address.zip and (" " + address.zip) or ""
                name += address.city and (" " + address.city) or ""

            first_res_da = fields.Date.from_string(first_res.date)
            date_propos_dt = datetime.combine(first_res_da, datetime.min.time()) + timedelta(hours=first_res.date_flo)  # datetime naive
            date_propos_dt = tz.localize(date_propos_dt, is_dst=None).astimezone(pytz.utc)  # datetime utc

            vals = {
                'date_display'    : first_res.date,
                'name'            : name,
                'user_id'       : first_res.user_id.id,
                'date_propos'     : date_propos_dt,  # datetime utc
                'date_propos_hour': first_res.date_flo,
                'res_line_id'     : first_res.id,
                'display_search'  : False,
                'display_res'     : True,
                'zero_result'     : False,
                'zero_dispo'      : False,
            }

            if nb_dispo == 0:
                vals['zero_dispo'] = True

        else:
            vals = {
                'display_search': True,
                'display_res' : False,
                'zero_result': True,
                'zero_dispo': False,
            }

        self.write(vals)
        if self.res_line_id:
            self.res_line_id.selected = True
            self.res_line_id.selected_hour = self.res_line_id.date_flo

    @api.multi
    def button_confirm(self):
        self.ensure_one()
        if self.creneau_ids[0].employee_id.id != self.employee_id.id:
            raise UserError(u"Il semblerait que vous ayez changé le commercial depuis votre dernière recherche. Veuillez relancer la recherche ou rétablir le commercial précédent (%s)" % self.creneau_ids[0].employee_id.name)
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        # tz = pytz.timezone(self._context['tz'])

        calendar_obj = self.env['calendar.event']

        # verifier que la date de début et la date de fin sont dans les créneaux
        td_pause_midi = timedelta(hours=self.hor_ad - self.hor_mf)
        td_pause_nuit = timedelta(hours=24 - self.hor_af + self.hor_md)
        date_propos_dt = fields.Datetime.from_string(self.date_propos)  # datetime utc proposition de rdv
        date_propos_deadline_dt = date_propos_dt + timedelta(hours=self.duree)  # datetime utc proposition fin de rdv
        propos_deadline_flo = self.date_propos_hour + self.duree
        found = False
        err = False
        for planning in self.creneau_ids:  # contrairement a rdv d'interventions, il n'y a qu'un seul commercial
            debut_dt = fields.Datetime.from_string(planning.debut_dt)
            fin_dt = fields.Datetime.from_string(planning.fin_dt)
            if err:
                continue
            elif debut_dt <= date_propos_dt <= fin_dt and not planning.calendar_id:  # le debut du rdv est dans un créneau dispo
                found = True
                if debut_dt <= date_propos_deadline_dt <= fin_dt:  # le rdv se termine dans ce même créneau
                    break
                elif self.date_propos_hour <= self.hor_mf and date_propos_deadline_dt > fin_dt:  # chevauchement pause midi
                    date_propos_deadline_dt += td_pause_midi
                    propos_deadline_flo += self.hor_ad - self.hor_mf
                elif self.date_propos_hour <= self.hor_af and date_propos_deadline_dt > fin_dt:  # chevauchement nuit
                    date_propos_deadline_dt += td_pause_nuit
                    propos_deadline_flo = (propos_deadline_flo + 24 - self.hor_af + self.hor_md) % 24
            elif found and planning.calendar_id:  # une intervention entre le début et la fin du rdv
                err = True
            elif found and debut_dt <= date_propos_deadline_dt <= fin_dt and not planning.calendar_id:  # la fin du rdv est dans un créneau dispo
                break
        else:
            raise UserError(u"Vérifier la date de RDV et l'équipe technique")

        if (not self.hor_md) or (not self.hor_mf) or (not self.hor_ad) or (not self.hor_af):
            raise UserError(u"Il faut configurer l'horaire de travail de toutes les équipes.")

        la_company = False
        l_adresse = False
        if self.lieu == "other":
            le_lieu = "offsite"
            l_adresse = self.lieu_rdv_id
        elif self.lieu == "customer":
            le_lieu = "offsite"
            l_adresse = self.partner_address_id
        elif self.lieu == "company":
            le_lieu = "onsite"
            la_company = self.lieu_company_id
            l_adresse = self.lieu_company_id.partner_id
        else:  # on phone
            le_lieu = "phone"

        values = {
            'name': self.name,
            'state': 'open',
            'start': fields.Datetime.to_string(date_propos_dt),
            'stop': fields.Datetime.to_string(date_propos_deadline_dt),
            'user_id': self.user_id.id,
            'allday': self.allday,
            'description': self.description or '',
            'partner_ids': [(4, self.user_id.partner_id.id, False), (4, self.partner_id.id, False)],
            'of_lieu': le_lieu,
            'of_lieu_rdv_id': l_adresse and l_adresse.id,
            'of_lieu_company_id': la_company and la_company.id,
            'opportunity_id': self.lead_id.id,
        }

        start = fields.Datetime.to_string(date_propos_dt)
        stop = fields.Datetime.to_string(date_propos_deadline_dt)
        existing = calendar_obj.search([('partner_ids', 'in', [self.user_id.partner_id.id, self.partner_id.id]),
                                        '|', '&', ('start', '>=', start), ('start', '<', stop),
                                             '&', ('stop', '>', start), ('stop', '<=', stop)])
        if existing.filtered(lambda c: self.user_id.partner_id in c.partner_ids):
            raise UserError(u"Le commercial a déjà 1 rendez-vous sur ce créneau ")
        elif existing.filtered(lambda c: self.partner_id in c.partner_ids):
            raise UserError(u"Le contact a déjà 1 rendez-vous sur ce créneau ")
        le_rdv = calendar_obj.create(values)

        le_rdv.attendee_ids.do_accept()

        return {'type': 'ir.actions.act_window_close'}

class OfRDVCommercialLine(models.TransientModel):
    _name = 'of.rdv.commercial.line'
    _description = 'Propositions des RDVs'
    _order = "date, date_flo"
    _inherit = "of.calendar.mixin"

    @api.model
    def calc_distances_dates(self, date_debut, date_fin, wizard_id):
        u"""
            une requete http par jour. En cas de problemes de performances on pourra se débrouiller pour faire une requête par équipe
        @TODO: revoir cette fonction, origine
        """
        un_jour = timedelta(days=1)
        date_courante = date_debut
        while date_courante <= date_fin:
            creneaux_pre = self.search([('date', '=', date_courante), ('wizard_id', '=', wizard_id)], order="debut_dt")
            creneaux_pre._compute_geo()
            creneaux = creneaux_pre.filtered(lambda c: c.geo_lat != 0.0 and c.geo_lng != 0.0)
            if len(creneaux) == 0:
                date_courante += un_jour
                continue

            origine = (creneaux[0].employee_id.of_address_depart_id or
                       creneaux[0].employee_id.address_id or
                       False)
            retour = (creneaux[0].employee_id.of_address_retour_id or
                      creneaux[0].employee_id.address_id or
                      False)
            if not origine:
                raise UserError(u"L'adressse de départ du commercial est manquante. Pour la configurer rendez-vous dans le menu Employés")
            if not retour:
                raise UserError(u"L'adressse de retour du commercial est manquante. Pour la configurer rendez-vous dans le menu Employés")
            if origine.geo_lat == origine.geo_lng == 0:
                raise UserError(u"L'adressse de départ du commercial n'est pas géolocalisée.")
            if retour.geo_lat == retour.geo_lng == 0:
                raise UserError(u"L'adressse de retour du commercial n'est pas géolocalisé.")

            coords_str = u""
            coords = []
            routing_base_url = config.get("of_routing_base_url", "")
            routing_version = config.get("of_routing_version", "")
            routing_profile = config.get("of_routing_profile", "")
            if not (routing_base_url and routing_version and routing_profile):
                query = "null"
            else:
                query = routing_base_url + u"route/" + routing_version + u"/" + routing_profile + u"/"

            # coordonnées du point de départ
            coords_str += str(origine.geo_lng) + u"," + str(origine.geo_lat)
            coords.append((origine.geo_lng, origine.geo_lat))

            # listess de coordonnées: ATTENTION OSRM prend ses coordonnées sous forme (lng, lat)
            # créneaux et rdvs
            for line in creneaux:
                # if line.geo_lat != 0 or line.geo_lng != 0: <- plus besoin: seulement créneaux géolocalisés dans la recherche
                coords_str += u";" + str(line.geo_lng) + u"," + str(line.geo_lat)
                coords.append((line.geo_lng, line.geo_lat))

            # coordonnées du point de retour
            coords_str += u";" + str(retour.geo_lng) + u"," + str(retour.geo_lat)
            coords.append((retour.geo_lng, retour.geo_lat))

            query_send = urllib.quote(query.strip().encode('utf8')).replace('%3A', ':')
            full_query = query_send + coords_str + "?"
            if len(coords) < 2:
                date_courante += un_jour
                continue
            try:
                req = requests.get(full_query)
                res = req.json()
            except Exception as e:
                res = {}

            if res and res.get(u"routes", False):
                legs = res[u"routes"][0][u"legs"]
                if len(creneaux) == len(legs) - 1:  # départ -> creneau -> retour : 2 routes 1 creneau
                    mode_recherche = creneaux[0].wizard_id.mode_recherche
                    maxi = creneaux[0].wizard_id.max_recherche
                    vals = []
                    for i in range(len(creneaux)):
                        vals.append({})
                        vals[i][u"dist_prec"] = legs[i][u"distance"] / 1000
                        vals[i][u"duree_prec"] = legs[i][u"duration"] / 60
                        vals[i][u"dist_suiv"] = legs[i+1][u"distance"] / 1000  # legs[i+1] ok car len(creneaux) == len(legs) - 1
                        vals[i][u"duree_suiv"] = legs[i+1][u"duration"] / 60  # legs[i+1] ok car len(creneaux) == len(legs) - 1
                        vals[i][u"distance"] = vals[i].get(u"dist_prec", 0) + vals[i].get(u"dist_suiv", 0)
                        vals[i][u"duree"] = vals[i].get(u"duree_prec", 0) + vals[i].get(u"duree_suiv", 0)
                        if i >= 1 and not (creneaux[i-1].calendar_id or creneaux[i].calendar_id):
                            # les creneaux précedant et actuel sont disponible, considérer qu'ils sont le même en terme de distances
                            vals[i][u"dist_prec"] = vals[i-1][u"dist_prec"]
                            vals[i][u"duree_prec"] = vals[i-1][u"duree_prec"]
                            vals[i-1][u"dist_suiv"] = vals[i][u"dist_suiv"]
                            vals[i-1][u"duree_suiv"] = vals[i][u"duree_suiv"]
                            vals[i][u"distance"] = vals[i][u"dist_suiv"] + vals[i-1][u"dist_prec"]
                            vals[i][u"duree"] = vals[i][u"duree_suiv"] + vals[i-1][u"duree_prec"]
                            vals[i-1][u"distance"] = vals[i][u"dist_suiv"] + vals[i-1][u"dist_prec"]
                            vals[i-1][u"duree"] = vals[i][u"duree_suiv"] + vals[i-1][u"duree_prec"]

                    for j in range(len(creneaux)):
                        # créneau plus loins que la recherche accepte
                        if creneaux[j].disponible and vals[j][mode_recherche] > maxi:
                            vals[j][u"force_color"] = "#FF0000"
                            vals[j][u"name"] = "TROP LOINS"
                            vals[j][u"disponible"] = False
                        creneaux[j].update(vals[j])
                else:
                    raise UserError("Erreur de res: %s - %s" % (len(creneaux), len(res[u"routes"][0][u"legs"])))
            elif res and res["message"]:
                raise UserError("Erreur de routing: %s" % res["message"])
            else:
                raise UserError("Erreur inattendue de routing")
            date_courante += un_jour

    @api.model
    def get_nb_dispo(self, wizard):
        """Retourne le nombre de créneaux disponibles (qui correspondent aux criteres de recherche),
            le nomre de créneau trop loins, et le premier resultat (en fonction du critere de résultat"""
        """if wizard.mode_result == "distance":
            le_order = "distance, debut_dt"
        else:
            le_order = "debut_dt, distance" """
        # ne pas inclure les lignes associées a une event ni les lignes de début et fin de recherche
        lines = self.search([('wizard_id', '=', wizard.id), ('virtuel', '=', False), ('calendar_id', '=', False)], order="distance, debut_dt")  # events allDay sont debut et fin de recherche
        lines_dispo = self.search([('wizard_id', '=', wizard.id), ('disponible', '=', True)], order="distance, debut_dt")
        nb = len(lines)
        nb_dispo = len(lines_dispo)
        first_res = lines_dispo and lines_dispo[0] or lines and lines[0] or False
        return (nb, nb_dispo, first_res)

    date = fields.Date(string="Date")
    debut_dt = fields.Datetime(string=u"Début")
    fin_dt = fields.Datetime(string="Fin")
    date_flo = fields.Float(string='Date', required=True, digits=(12, 5))
    date_flo_deadline = fields.Float(string='Date', required=True, digits=(12, 5))
    description = fields.Char(string='Plage horaire', size=128)
    wizard_id = fields.Many2one('of.rdv.commercial', string="RDV", required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string="Compte utilisateur")
    employee_id = fields.Many2one('hr.employee', string="Commercial")
    user_partner_id = fields.Many2one('res.partner', string="user partner")
    partner_ids = fields.Many2many('res.partner', 'calendar_event_res_rdvcom_rel', string='Attendees')
    calendar_id = fields.Many2one('calendar.event', string="Planning")
    categ_ids = fields.Many2many(
        'calendar.event.type', 'rdvcom_meeting_category_rel', 'rdvcomline_id', 'type_id', 'Tags')
    name = fields.Char(string="name", default="DISPONIBLE")
    distance = fields.Float(string='Dist.tot. (km)', help="distance prec + distance suiv", digits=(12, 1))
    dist_prec = fields.Float(string='Dist.Prec. (km)', digits=(12, 1))
    dist_suiv = fields.Float(string='Dist.Suiv. (km)', digits=(12, 1))
    duree = fields.Float(string=u'Durée.tot. (min)', help="durée prec + durée suiv", digits=(12, 0))
    duree_prec = fields.Float(string=u'Durée.Prec. (min)', digits=(12, 0))
    duree_suiv = fields.Float(string=u'Durée.Suiv. (min)', digits=(12, 0))
    of_color_ft = fields.Char(related="user_id.of_color_ft", readonly=True)
    of_color_bg = fields.Char(related="user_id.of_color_bg", readonly=True)
    disponible = fields.Boolean(string="Est dispo", default=True)
    force_color = fields.Char("Couleur")
    allday = fields.Boolean('All Day', default=False)
    virtuel = fields.Boolean('Virtuel', default=False)
    selected = fields.Boolean(u'Créneau sélectionné', default=False)
    selected_hour = fields.Float(string='Heure du RDV', digits=(2, 2))
    selected_description = fields.Html(string="Description", related="wizard_id.description")
    on_phone = fields.Boolean(u'Au téléphone', default=False)

    ignorer_geo = fields.Boolean(u"Ignorer données géographiques")
    geo_lat = fields.Float(
        string='Geo Lat', digits=(8, 8), group_operator=False, help="latitude field", compute="_compute_geo",
        readonly=True, search='_search_lat')
    geo_lng = fields.Float(
        string='Geo Lng', digits=(8, 8), group_operator=False, help="longitude field", compute="_compute_geo",
        readonly=True, search='_search_lng')
    precision = fields.Selection(
        GEO_PRECISION, default='not_tried', readonly=True, compute="_compute_geo", search='_search_precision',
        help=u"Niveau de précision de la géolocalisation.\n"
             u"bas: à la ville.\n"
             u"moyen: au village\n"
             u"haut: à la rue / au voisinage\n"
             u"très haut: au numéro de rue\n")

    def _search_lat(self, operator, operand):
        calendars = self.env['calendar.event']
        wizards = self.env['of.rdv.commercial']
        for line in self:
            if line.calendar_id:
                calendars |= line.calendar_id
            else:
                wizards |= line.wizard_id
        calendars = calendars.search([('id', 'in', calendars._ids), ('of_geo_lat', operator, operand)])
        wizards = wizards.search([('id', 'in', wizards._ids), ('geo_lat', operator, operand)])
        return [('id', 'in', self.env['of.rdv.commercial.line'].search(['|', ('calendar_id', 'in', calendars._ids),
                                                                             ('wizard_id', 'in', wizards._ids)])._ids)]

    def _search_lng(self, operator, operand):
        calendars = self.env['calendar.event']
        wizards = self.env['of.rdv.commercial']
        for line in self:
            if line.calendar_id:
                calendars |= line.calendar_id
            else:
                wizards |= line.wizard_id
        calendars = calendars.search([('id', 'in', calendars._ids), ('of_geo_lng', operator, operand)])
        wizards = wizards.search([('id', 'in', wizards._ids), ('geo_lng', operator, operand)])
        return [('id', 'in', self.env['of.rdv.commercial.line'].search(['|', ('calendar_id', 'in', calendars._ids),
                                                                             ('wizard_id', 'in', wizards._ids)])._ids)]

    def _search_precision(self, operator, operand):
        calendars = self.env['calendar.event']
        wizards = self.env['of.rdv.commercial']
        for line in self:
            if line.calendar_id:
                calendars |= line.calendar_id
            else:
                wizards |= line.wizard_id
        calendars = calendars.search([('id', 'in', calendars._ids), ('of_precision', operator, operand)])
        wizards = wizards.search([('id', 'in', wizards._ids), ('precision', operator, operand)])
        return [('id', 'in', self.env['of.rdv.commercial.line'].search(['|', ('calendar_id', 'in', calendars._ids),
                                                                             ('wizard_id', 'in', wizards._ids)])._ids)]

    @api.multi
    @api.depends("calendar_id")
    def _compute_geo(self):
        for line in self:
            if line.calendar_id:  # correspond a un creneau d'intervention
                vals = {
                    'geo_lat': line.calendar_id.of_geo_lat,
                    'geo_lng': line.calendar_id.of_geo_lng,
                    'precision': line.calendar_id.of_precision,
                }
            else:  # correspond a un creneau libre
                vals = {
                    'geo_lat': line.wizard_id.geo_lat,
                    'geo_lng': line.wizard_id.geo_lng,
                    'precision': line.wizard_id.precision,
                }
            line.update(vals)

    @api.depends('calendar_id')
    def _compute_state_int(self):
        """de of.calendar.mixin"""
        for line in self:
            interv = line.calendar_id
            if interv:
                if interv.state and interv.state == "draft":
                    line.state_int = 0
                elif interv.state and interv.state == "open":
                    line.state_int = 1
                elif interv.state and interv.state == "done":
                    line.state_int = 2
            else:
                line.state_int = 3

    @api.model
    def get_state_int_map(self):
        """de of.calendar.mixin"""
        v0 = {'label': 'Brouillon', 'value': 0}
        v1 = {'label': u'Confirmé', 'value': 1}
        v2 = {'label': u'Réalisé', 'value': 2}
        v3 = {'label': u'Disponibilité', 'value': 3}
        return (v0, v1, False, v3)

    @api.multi
    def button_confirm(self):
        """Sélectionne ce créneau en temps que résultat. Appelé depuis la vue form du créneau"""
        self.ensure_one()
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        tz = pytz.timezone(self._context['tz'])
        d = fields.Date.from_string(self.date)
        date_propos_dt = datetime.combine(d, datetime.min.time()) + timedelta(hours=self.selected_hour)  # datetime local
        date_propos_dt = tz.localize(date_propos_dt, is_dst=None).astimezone(pytz.utc)  # datetime utc
        self.wizard_id.date_propos = date_propos_dt
        return self.wizard_id.button_confirm()

    @api.multi
    def button_select(self):
        """Sélectionne ce créneau en temps que résultat. Appelé depuis la vue form du créneau"""
        self.ensure_one()
        rdv_line_obj = self.env["of.rdv.commercial.line"]
        selected_line = rdv_line_obj.search([("selected", "=", True), ("wizard_id", "=", self.wizard_id.id)])
        selected_line.selected = False
        self.selected = True
        self.selected_hour = self.date_flo

        if self.wizard_id.lieu == 'company':
            address = self.wizard_id.lieu_company_id
        elif self.wizard_id.lieu == 'other':
            address = self.wizard_id.lieu_rdv_id
        else:
            address = self.wizard_id.partner_address_id
        name = address.name or (address.parent_id and address.parent_id.name) or ''
        if self.wizard_id.lieu == 'phone':
            name += u' (téléphonique)'
        else:
            name += address.zip and (" " + address.zip) or ""
            name += address.city and (" " + address.city) or ""
        wizard_vals = {
            'date_display'    : self.date,  # .strftime('%A %d %B %Y'),
            'name'            : name,
            'date_propos'     : self.debut_dt,
            'date_propos_hour': self.date_flo,
            'res_line_id'     : self.id,
        }
        self.wizard_id.write(wizard_vals)

        return {'type': 'ir.actions.do_nothing'}
