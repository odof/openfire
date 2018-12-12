# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError
import pytz
from datetime import datetime

@api.model
def _tz_get(self):
    # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
    return [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

class OFUsers(models.Model):
    _inherit = 'res.users'

    of_color_ft = fields.Char(string="Couleur de texte", help="Choisissez votre couleur", default="#0D0D0D", oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", help="Choisissez votre couleur", default="#F0F0F0", oldname="color_bg")

class OFPartners(models.Model):
    _inherit = 'res.partner'

    of_color_ft = fields.Char(string="Couleur de texte", compute="_compute_colors", oldname="color_ft")
    of_color_bg = fields.Char(string="Couleur de fond", compute="_compute_colors", oldname="color_bg")

    @api.depends("user_ids")
    def _compute_colors(self):
        for partner in self:
            if partner.user_ids:
                partner.of_color_ft = partner.user_ids[0].of_color_ft
                partner.of_color_bg = partner.user_ids[0].of_color_bg
            else:
                partner.of_color_ft = "#0D0D0D"
                partner.of_color_bg = "#F0F0F0"

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_default_jours(self):
        # Lundi à vendredi comme valeurs par défaut
        jours = self.env['of.jours'].search([('numero', 'in', (1, 2, 3, 4, 5))], order="numero")
        res = [jour.id for jour in jours]
        return res

    hor_md = fields.Float(string=u'Matin début', required=True, digits=(12, 1),default=9)
    hor_mf = fields.Float(string='Matin fin', required=True, digits=(12, 1),default=12)
    hor_ad = fields.Float(string=u'Après-midi début', required=True, digits=(12, 1),default=14)
    hor_af = fields.Float(string=u'Après-midi fin', required=True, digits=(12, 1),default=18)
    jour_ids = fields.Many2many('of.jours', 'employee_jours_rel', 'employee_id', 'jour_id', string='Jours travaillés', required=True, default=_get_default_jours)
    tz = fields.Selection(_tz_get, string='Fuseau horaire', default=lambda self: self.env.user.tz or 'Europe/Paris', required=True,
                          help="The Team's timezone, used to output proper date and time values "
                               "inside printed reports. It is important to set a value for this field. "
                               "You should use the same timezone that is otherwise used to pick and "
                               "render date and time values: your computer's timezone.")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset')
    address_depart_id = fields.Many2one('res.partner', string=u'Adresse de départ')
    address_retour_id = fields.Many2one('res.partner', string='Adresse de retour')

    of_color_ft = fields.Char(string="Couleur de texte", compute="_compute_colors")
    of_color_bg = fields.Char(string="Couleur de fond", compute="_compute_colors")

    @api.depends('tz')
    def _compute_tz_offset(self):
        for wizard in self:
            wizard.tz_offset = datetime.now(pytz.timezone(wizard.tz or 'GMT')).strftime('%z')

    @api.depends("user_id")
    def _compute_colors(self):
        for employee in self:
            if employee.user_id:
                employee.of_color_ft = employee.user_id.of_color_ft
                employee.of_color_bg = employee.user_id.of_color_bg
            else:
                employee.of_color_ft = "#0D0D0D"
                employee.of_color_bg = "#F0F0F0"

    _sql_constraints = [
        ('hor_md_mf_constraint', 'CHECK ( hor_md <= hor_mf )', _(u"L'Heure de début de matinée doit être antérieure à l'heure de fin de matinée")),
        ('hor_mf_ad_constraint', 'CHECK ( hor_mf <= hor_ad )', _(u"L'Heure de fin de matinée doit être antérieure à l'heure de début d'après-midi")),
        ('hor_ad_af_constraint', 'CHECK ( hor_ad <= hor_af )', _(u"L'Heure de début d'après-midi doit être antérieure à l'heure de fin d'après-midi")),
    ]

    @api.onchange('address_depart_id')
    def _onchange_address_depart_id(self):
        self.ensure_one()
        if self.address_depart_id:
            self.address_retour_id = self.address_depart_id

    @api.onchange('user_id')
    def _onchange_user_id(self):
        self.ensure_one()
        if self.user_id:
            self.tz = self.user_id.tz

    @api.onchange('hor_md')
    def _onchange_hor_md(self):
        self.ensure_one()
        if self.hor_md and self.hor_mf and self.hor_md > self.hor_mf:
            raise UserError(u"L'Heure de début de matinée doit être antérieure à l'heure de fin de matinée")

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

    @api.model
    def get_working_hours_fields(self):
        return {
            "morning_start_field": "hor_md",
            "morning_end_field": "hor_mf",
            "afternoon_start_field": "hor_ad",
            "afternoon_end_field": "hor_af"
        }

class OFMeetingType(models.Model):
    _inherit = 'calendar.event.type'

    active = fields.Boolean("Actif",default=True)

class OFMeeting(models.Model):
    _inherit = "calendar.event"

    #redefinition
    description = fields.Html('Description', states={'done': [('readonly', True)]})
    location = fields.Char('Location', compute="_compute_location", store=True, track_visibility='onchange', help="Location of Event")

    lieu = fields.Selection([
        ("onsite", "Dans les locaux"),
        ("phone", "Au téléphone"),
        ("offsite", "À l'exterieur"),
        ("custom", "Adresse manuelle"),
        ], string="Lieu du RDV", required=True, default="onsite")
    #user_company_ids = fields.Many2many('res.company', 'calendar_user_company_rel', 'calendar_id', 'company_id', u"sociétés du propriétaire",compute="_compute_user_company_ids")#,store=True)#related="user_id.company_ids", readonly=True)
    # tentative de domain ratée
    lieu_company_id = fields.Many2one("res.company",string="(Précisez)")#,domain="[('id', 'in', user_company_ids and user_company_ids._ids)]")
    lieu_rdv_id = fields.Many2one("res.partner",string="(Précisez)")
    lieu_address_street = fields.Char(string="Rue")#, compute="_compute_geo")
    lieu_address_street2 = fields.Char(string="Rue (2)")#, compute="_compute_geo")
    lieu_address_city = fields.Char(string="Ville")#, compute="_compute_geo")
    lieu_address_state_id = fields.Many2one("res.country.state", string=u"Région")#, compute="_compute_geo")
    lieu_address_zip = fields.Char(string="Code postal")#, compute="_compute_geo")
    lieu_address_country_id = fields.Many2one("res.country", string="Pays")#, compute="_compute_geo")
    on_phone = fields.Boolean(u'Au téléphone', compute="_compute_on_phone")
    color_partner_id = fields.Many2one("res.partner", "Partner whose color we will take", compute='_compute_color_partner', store=False)
    geo_lat = fields.Float(string='Geo Lat', digits=(8, 8), group_operator=False, help="latitude field", compute="_compute_geo", store=False, search='_search_lat')
    geo_lng = fields.Float(string='Geo Lng', digits=(8, 8), group_operator=False, help="longitude field", compute="_compute_geo", store=False, search='_search_lng')
    precision = fields.Selection([
        ('manual', "Manuel"),
        ('high', "Haut"),
        ('medium', "Moyen"),
        ('low', "Bas"),
        ('no_address', u"--"),
        ('unknown', u"Indéterminé"),
        ('not_tried', u"Pas tenté"),
        ], default='not_tried', help=u"Niveau de précision de la géolocalisation", compute="_compute_geo", store=False, search='_search_precision')

    def _search_lat(self, operator, operand):
        partners = self.env['res.partner']
        companies = self.env['res.company']
        for meeting in self:
            if meeting.lieu and meeting.lieu == "onsite":
                companies |= meeting.lieu_company_id.partner_id  # lieu_company_id est res.company
            elif meeting.lieu and meeting.lieu == "offsite":
                partners |= meeting.lieu_rdv_id
            elif meeting.lieu and meeting.lieu == "phone":
                continue
            else:
                continue
        partners = partners.search([('id', 'in', partners._ids), ('geo_lat', operator, operand)])
        companies = companies.search([('id', 'in', companies._ids), ('partner_id.geo_lat', operator, operand)])
        return [('id', 'in', self.env['calendar.event'].search(['|',
                                                                    '&', ('lieu_company_id', 'in', companies._ids),
                                                                         ('lieu', '=', 'onsite'),
                                                                    '&', ('lieu_rdv_id', 'in', partners._ids),
                                                                         ('lieu', '=', 'offsite')])._ids)]

    def _search_lng(self, operator, operand):
        partners = self.env['res.partner']
        companies = self.env['res.company']
        for meeting in self:
            if meeting.lieu and meeting.lieu == "onsite":
                companies |= meeting.lieu_company_id.partner_id  # lieu_company_id est res.company
            elif meeting.lieu and meeting.lieu == "offsite":
                partners |= meeting.lieu_rdv_id
            elif meeting.lieu and meeting.lieu == "phone":
                continue
            else:
                continue
        partners = partners.search([('id', 'in', partners._ids), ('geo_lng', operator, operand)])
        companies = companies.search([('id', 'in', companies._ids), ('partner_id.geo_lng', operator, operand)])
        return [('id', 'in', self.env['calendar.event'].search(['|',
                                                                    '&', ('lieu_company_id', 'in', companies._ids),
                                                                         ('lieu', '=', 'onsite'),
                                                                    '&', ('lieu_rdv_id', 'in', partners._ids),
                                                                         ('lieu', '=', 'offsite')])._ids)]

    def _search_precision(self, operator, operand):
        partners = self.env['res.partner']
        companies = self.env['res.company']
        for meeting in self:
            if meeting.lieu and meeting.lieu == "onsite":
                companies |= meeting.lieu_company_id.partner_id  # lieu_company_id est res.company
            elif meeting.lieu and meeting.lieu == "offsite":
                partners |= meeting.lieu_rdv_id
            elif meeting.lieu and meeting.lieu == "phone":
                continue
            else:
                continue
        partners = partners.search([('id', 'in', partners._ids), ('precision', operator, operand)])
        companies = companies.search([('id', 'in', companies._ids), ('partner_id.precision', operator, operand)])
        return [('id', 'in', self.env['calendar.event'].search(['|',
                                                                    '&', ('lieu_company_id', 'in', companies._ids),
                                                                         ('lieu', '=', 'onsite'),
                                                                    '&', ('lieu_rdv_id', 'in', partners._ids),
                                                                         ('lieu', '=', 'offsite')])._ids)]

    @api.multi
    @api.depends("lieu")
    def _compute_on_phone(self):
        for meeting in self:
            if meeting.lieu and meeting.lieu == "phone":
                meeting.on_phone = True

    @api.multi
    @api.depends("lieu","lieu_company_id","lieu_rdv_id")
    def _compute_geo(self):
        for meeting in self:
            if meeting.lieu and meeting.lieu == "onsite": # dans les locaux
                vals = {
                    "lieu_address_street": meeting.lieu_company_id.street,
                    "lieu_address_street2": meeting.lieu_company_id.street2,
                    "lieu_address_city": meeting.lieu_company_id.city,
                    "lieu_address_state_id": meeting.lieu_company_id.state_id.id,
                    "lieu_address_zip": meeting.lieu_company_id.zip,
                    "lieu_address_country_id": meeting.lieu_company_id.country_id.id,
                    'geo_lat': meeting.lieu_company_id.geo_lat,
                    'geo_lng': meeting.lieu_company_id.geo_lng,
                    'precision': meeting.lieu_company_id.precision,
                }
            elif meeting.lieu and meeting.lieu == "offsite": # a l'exterieur
                vals = {
                    "lieu_address_street": meeting.lieu_rdv_id.street,
                    "lieu_address_street2": meeting.lieu_rdv_id.street2,
                    "lieu_address_city": meeting.lieu_rdv_id.city,
                    "lieu_address_state_id": meeting.lieu_rdv_id.state_id.id,
                    "lieu_address_zip": meeting.lieu_rdv_id.zip,
                    "lieu_address_country_id": meeting.lieu_rdv_id.country_id.id,
                    'geo_lat': meeting.lieu_rdv_id.geo_lat,
                    'geo_lng': meeting.lieu_rdv_id.geo_lng,
                    'precision': meeting.lieu_rdv_id.precision,
                }
            elif meeting.lieu and meeting.lieu == "phone": # au téléphone
                vals = {
                    "lieu_address_street": False,
                    "lieu_address_street2": False,
                    "lieu_address_city": False,
                    "lieu_address_state_id": False,
                    "lieu_address_zip": False,
                    "lieu_address_country_id": False,
                    'geo_lat': 0,
                    'geo_lng': 0,
                    'precision': 'no_address',
                }
            else: # custom
                vals = {
                    'geo_lat': 0,
                    'geo_lng': 0,
                    'precision': 'not_tried',
                }
            meeting.update(vals)

    @api.multi
    @api.depends("lieu","lieu_company_id","lieu_rdv_id","precision","lieu_address_street","lieu_address_street2",
                 "lieu_address_city","lieu_address_state_id","lieu_address_zip","lieu_address_country_id")
    def _compute_location(self):
        for meeting in self:
            if meeting.precision != "no_address":
                le_tab = []
                le_texte = ""
                """
                On remplit le tableau puis on crée le texte
                """
                if meeting.lieu_address_street:
                    le_tab.append(meeting.lieu_address_street)
                if meeting.lieu_address_street2:
                    le_tab.append(meeting.lieu_address_street2)
                if meeting.lieu_address_city and meeting.lieu_address_zip:
                    le_tab.append(meeting.lieu_address_zip + " " + meeting.lieu_address_city)
                elif meeting.lieu_address_city:
                    le_tab.append(meeting.lieu_address_city)
                elif meeting.lieu_address_zip:
                    le_tab.append(meeting.lieu_address_zip)
                if meeting.lieu_address_state_id:
                    le_tab.append(meeting.lieu_address_state_id.name)
                if meeting.lieu_address_country_id:
                    le_tab.append(meeting.lieu_address_country_id.name)
                if len(le_tab) > 0:
                    le_texte += le_tab[0]
                for i in range(1,len(le_tab)):
                    le_texte += ", " + le_tab[i]
                meeting.location = le_texte

    """tentative de domain ratée
    @api.multi
    @api.depends("user_id.company_ids")
    def _compute_user_company_ids(self):
        for meeting in self:
            la_list = []
            #meeting.user_company_ids = [(5,0,0)] + [(4,le_id,False) for le_id in meeting.user_id.company_ids._ids]
            if meeting.user_id.id:
                company_ids = meeting.user_id.company_ids
                la_list = [x.id for x in company_ids]
            meeting.user_company_ids = [(6,0,la_list)]"""

    @api.onchange('lieu')
    def _onchange_lieu(self):
        self.ensure_one()
        if not self.lieu or self.lieu  == "phone": # réinitialise
            self.lieu_rdv_id = False
            self.lieu_company_id = False
        elif self.lieu == "onsite": # on site
            self.lieu_company_id = self.user_id.company_id.id
            self.lieu_rdv_id = self.user_id.company_id.partner_id.id
        else: # off site
            self.lieu_company_id = False

    @api.onchange('lieu_company_id')
    def _onchange_lieu_company_id(self):
        self.ensure_one()
        if not self.lieu or not self.lieu == "onsite":
            return
        if not self.lieu_company_id:
            return
        self.lieu_rdv_id = self.lieu_company_id.partner_id.id

    """
    These fields would be necessary if use_contacts="0" in <calendar>. See event_data_transform function in .js file

    of_color_ft = fields.Char(string="Couleur de texte", help="Couleur de texte de l'utilisateur", compute="_compute_of_color")
    of_color_bg = fields.Char(string="Couleur de fond", help="Couleur de fond de l'utilisateur", compute="_compute_of_color")

    @api.multi
    @api.depends('color_partner_id')
    def _compute_of_color(self):
        for meeting in self:
            meeting.of_color_bg = meeting.color_partner_id.of_color_bg
            meeting.of_color_ft = meeting.color_partner_id.of_color_ft
    """

    @api.multi
    @api.depends('user_id')
    def _compute_color_partner(self):
        for meeting in self:
            if meeting.user_id.partner_id in meeting.partner_ids:
                meeting.color_partner_id = meeting.user_id.partner_id
            else:
                meeting.color_partner_id = (filter(lambda partner:partner.user_ids, meeting.partner_ids) or [False])[0]

    @api.multi
    def write(self, vals):
        if vals.get('lieu_rdv_id', False) or vals.get('lieu_company_id', False):
            le_lieu = vals.get('lieu', False)
            if not le_lieu:
                le_lieu = self.env["calendar.event"].browse(self._ids[0]).lieu
            if le_lieu == "onsite":
                la_company = self.env["res.company"].browse(vals.get("lieu_company_id",False))
                vals["lieu_address_street"] = la_company.partner_id.street
                vals["lieu_address_street2"] = la_company.partner_id.street2
                vals["lieu_address_city"] = la_company.partner_id.city
                vals["lieu_address_state_id"] = la_company.partner_id.state_id.id
                vals["lieu_address_zip"] = la_company.partner_id.zip
                vals["lieu_address_country_id"] = la_company.partner_id.country_id.id
            elif le_lieu == "offsite":
                le_partner = self.env["res.partner"].browse(vals.get("lieu_rdv_id"))
                vals["lieu_address_street"] = le_partner.street
                vals["lieu_address_street2"] = le_partner.street2
                vals["lieu_address_city"] = le_partner.city
                vals["lieu_address_state_id"] = le_partner.state_id.id
                vals["lieu_address_zip"] = le_partner.zip
                vals["lieu_address_country_id"] = le_partner.country_id.id
            elif le_lieu == "phone":
                vals["lieu_address_street"] = False
                vals["lieu_address_street2"] = False
                vals["lieu_address_city"] = False
                vals["lieu_address_state_id"] = False
                vals["lieu_address_zip"] = False
                vals["lieu_address_country_id"] = False
                vals["geo_lat"] = False
                vals["geo_lng"] = False
                vals["precision"] = "no_address"
        return super(OFMeeting, self).write(vals)

    @api.model
    def create(self, vals):
        """
        En cas de création par google agenda, le champs "location" peut etre renseigné, or dans ce module on transforme ce champ en champ calculé
        """
        le_lieu = vals.get('lieu', False)
        if not le_lieu:
            vals["lieu"] = "custom"
        else:
            if le_lieu == "onsite":
                la_company = self.env["res.company"].browse(vals.get("lieu_company_id"))
                vals["lieu_address_street"] = la_company.partner_id.street
                vals["lieu_address_street2"] = la_company.partner_id.street2
                vals["lieu_address_city"] = la_company.partner_id.city
                vals["lieu_address_state_id"] = la_company.partner_id.state_id.id
                vals["lieu_address_zip"] = la_company.partner_id.zip
                vals["lieu_address_country_id"] = la_company.partner_id.country_id.id
            elif le_lieu == "offsite":
                le_partner = self.env["res.partner"].browse(vals.get("lieu_rdv_id"))
                vals["lieu_address_street"] = le_partner.street
                vals["lieu_address_street2"] = le_partner.street2
                vals["lieu_address_city"] = le_partner.city
                vals["lieu_address_state_id"] = le_partner.state_id.id
                vals["lieu_address_zip"] = le_partner.zip
                vals["lieu_address_country_id"] = le_partner.country_id.id
            elif le_lieu == "phone":
                vals["lieu_address_street"] = False
                vals["lieu_address_street2"] = False
                vals["lieu_address_city"] = False
                vals["lieu_address_state_id"] = False
                vals["lieu_address_zip"] = False
                vals["lieu_address_country_id"] = False
        loc = vals.get("location", False)
        if loc:  # created from google agenda most likely
            vals["lieu_address_street"] = loc
            vals["lieu"] = "custom"
        return super(OFMeeting, self).create(vals)

class OFCalendarMixin(models.AbstractModel):
    _name = "of.calendar.mixin"

    state_int = fields.Integer(string="Valeur d'état", compute="_compute_state_int", help="valeur allant de 0 à 3 inclus")

    def _compute_state_int(self):
        """
        Function to give an integer value (0,1,2 or 3) depending on the state. ONLY 4 values are implemented.
        A CSS class 'of_calendar_state_#{self.state_int} will be given in CalendarView.event_data_transform.
        See .less and .js files for further information
        """
        raise NotImplementedError("A class inheriting from this one must implement a '_compute_state_int' function")

    @api.model
    def get_state_int_map(self):
        """
        Returns a tuple of dictionaries. Each one contains 'value' and 'label' attributes.
        'value' ranges from 0 to 3 included.
        'label' is a string that will be displayed in the caption.
        See template 'CalendarView.sidebar.captions'
        """
        raise NotImplementedError("A class inheriting from this one must implement a 'get_state_int_map' function")

class OFCalendarAttendeeMixin(models.AbstractModel):
    _name = "of.calendar.attendee.mixin"

    @api.model
    def get_working_hours_fields(self):
        """
        Returns a dictionnary with 4 properties: morning_start, morning_end, afternoon_start, afternoon_end
        these properties have names of corresponding fields as values
        """
        raise NotImplementedError("A class inheriting from this one must implement a 'get_state_int_map' function")
