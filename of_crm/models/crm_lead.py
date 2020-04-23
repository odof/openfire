# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime
from datetime import timedelta
import time
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'of.map.view.mixin']

    @api.model_cr_context
    def _auto_init(self):
        """
        Changement du fonctionnement des tag_ids de crm.lead pour que le champ soit
        related a partner_id.category_id donc ajout des tags présent sur le crm.lead
        dans le res.partner associé
        """
        cr = self._cr
        cr.execute("SELECT 1 FROM ir_model_fields WHERE model = 'crm.lead' AND name = 'tag_ids' "
                   "AND (related IS NULL OR related = '')")
        if cr.fetchall():
            # Remplissage des étiquettes partenaire manquantes à partir des étiquettes du pipeline
            cr.execute("INSERT INTO res_partner_res_partner_category_rel(partner_id, category_id) "
                       "SELECT lead.partner_id, rel.category_id "
                       "FROM crm_lead lead "
                       "INNER JOIN crm_lead_res_partner_category_rel rel ON rel.lead_id = lead.id "
                       "WHERE lead.partner_id IS NOT NULL "
                       "ON CONFLICT DO NOTHING")
        res = super(CrmLead, self)._auto_init()
        return res

    @api.model
    def _init_clients(self):
        partner_obj = self.env['res.partner']

        account_obj = self.env['account.account']
        # Desactivation du recalcul du _parent_order pour gagner du temps (beaucoup de temps)
        account_parent_store = account_obj._parent_store
        account_obj._parent_store = False

        cr = self._cr
        cr.execute("SELECT id, street, street2, zip, city, state_id, country_id, phone, fax, "
                   "       mobile, email_from AS email, COALESCE(partner_name, name) AS name, "
                   "       company_id "
                   "FROM crm_lead "
                   "WHERE partner_id IS NULL")
        columns = [column[0] for column in cr.description]
        for partner_data in cr.fetchall():
            # Création du partenaire associé
            partner_data_dict = dict(zip(columns, partner_data))
            lead = self.browse(partner_data_dict.pop('id'))
            partner_data_dict.update({
                'customer': True,
                'of_customer_state': 'lead',
            })
            lead.partner_id = partner_obj.create(partner_data_dict)

        # Recalcul des colonnes parent_left,parent_right
        account_obj._parent_store = account_parent_store
        account_obj._parent_store_compute()

    of_website = fields.Char(related="partner_id.website")
    of_description_projet = fields.Html('Notes de projet')  # champs inutile à supprimer bientôt
    of_ref = fields.Char(string=u"Référence", copy=False)
    of_prospecteur_id = fields.Many2one("res.users", string="Prospecteur", oldname='of_prospecteur')
    of_date_prospection = fields.Date(string="Date de prospection", default=fields.Date.today)
    # @TODO: implémenter la maj automatique de la date de cloture en fonction du passage de probabilité à 0 ou 100
    of_date_cloture = fields.Date(string=u"Date de clôture")
    of_infos_compl = fields.Html(string="Autres infos")
    geo_lat = fields.Float(related="partner_id.geo_lat")
    geo_lng = fields.Float(related="partner_id.geo_lng")
    precision = fields.Selection(related='partner_id.precision')
    stage_probability = fields.Float(related="stage_id.probability", readonly=True)

    of_projet_line_ids = fields.One2many('of.crm.projet.line', 'lead_id', string=u'Entrées')
    of_modele_id = fields.Many2one('of.crm.projet.modele', string=u"Projet", ondelete="set null")

    of_customer_state = fields.Selection(related="partner_id.of_customer_state", required=False)
    is_company = fields.Boolean(string=u"Est une société")
    # activity_ids = fields.One2many('of.crm.opportunity.activity', 'lead_id', string=u"Activités de cette opportunité")

    # surcharges
    tag_ids = fields.Many2many(
        'res.partner.category', related="partner_id.category_id", string='Tags',
        help="Classify and analyze your lead/opportunity categories like: Training, Service", oldname="of_tag_ids")
    of_referred_id = fields.Many2one('res.partner', string=u"Apporté par", help="Nom de l'apporteur d'affaire")
    street = fields.Char(related='partner_id.street')
    street2 = fields.Char(related='partner_id.street2')
    zip = fields.Char(related='partner_id.zip')
    city = fields.Char(related='partner_id.city')
    state_id = fields.Many2one(related="partner_id.state_id")
    country_id = fields.Many2one(related='partner_id.country_id')
    phone = fields.Char(related='partner_id.phone')
    fax = fields.Char(related='partner_id.fax')
    mobile = fields.Char(related='partner_id.mobile')
    email_from = fields.Char(related="partner_id.email")
    description = fields.Html(string="Suivi")
    description_rapport = fields.Html(string="Suivi bis", compute="_compute_description_rapport")
    user_id = fields.Many2one(help=u"La couleur des activités en vue calendrier est celle du commercial")

    meeting_ids = fields.Many2many('calendar.event', string=u"Réunions", related="partner_id.meeting_ids")
    # custom colors
    of_color_ft = fields.Char(string="Couleur de texte", compute="_compute_custom_colors")
    of_color_bg = fields.Char(string="Couleur de fond", compute="_compute_custom_colors")
    # city completion
    zip_id = fields.Many2one('res.better.zip', 'City/Location')

    # Pour l'infobulle de la vue map
    next_activity_name = fields.Char(related='next_activity_id.name')
    of_color_map = fields.Char(string="Couleur du marqueur", compute="_compute_of_color_map")

    @api.depends('description')
    def _compute_description_rapport(self):
        for lead in self:
            lead.description_rapport = lead.description and lead.description.replace("<p>", "").replace("</p>", "<br/>")

    @api.multi
    @api.depends('user_id')
    def _compute_custom_colors(self):
        for lead in self:
            if lead.user_id:
                lead.of_color_ft = lead.user_id.of_color_ft
                lead.of_color_bg = lead.user_id.of_color_bg
            else:
                lead.of_color_ft = "#0D0D0D"
                lead.of_color_bg = "#F0F0F0"

    @api.multi
    @api.depends('date_action')
    def _compute_of_color_map(self):
        date_today = fields.Date.from_string(fields.Date.today())

        for lead in self:
            color = 'gray'
            if lead.date_action:
                date_action = fields.Date.from_string(lead.date_action)
                if date_action > date_today + timedelta(days=30):  # prochaine action dans plus d'un mois
                    color = "blue"
                elif date_action >= date_today:  # prochaine action dans moins d'un mois
                    color = "orange"
                else:  # prochaine action en retard
                    color = "red"
            lead.of_color_map = color

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id.user_id:
            self.user_id = self.partner_id.user_id

    @api.onchange('zip_id')
    def onchange_zip_id(self):
        if self.zip_id:
            self.zip = self.zip_id.name
            self.city = self.zip_id.city
            self.state_id = self.zip_id.state_id
            self.country_id = self.zip_id.country_id

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        values = self._onchange_stage_id_values(self.stage_id.id)
        if values.get('probability') == 100 and self.of_customer_state and self.of_customer_state != "customer":
            values['of_customer_state'] = "customer"
        self.update(values)

    @api.onchange('of_modele_id')
    def _onchange_modele_id(self):
        for projet in self:
            if projet.of_modele_id:
                projet.update({'of_projet_line_ids': [(5, )]})
                attr_vals = {}
                vals = []
                for attr in projet.of_modele_id.attr_ids:
                    attr_vals['attr_id'] = attr.id
                    attr_vals['type'] = attr.type
                    attr_vals['name'] = attr.name
                    attr_vals['sequence'] = attr.sequence
                    the_type = attr.type
                    if the_type == 'char':
                        attr_vals['val_char'] = attr.val_char_default
                    elif the_type == 'text':
                        attr_vals['val_text'] = attr.val_text_default
                    elif the_type == 'selection':
                        attr_vals['val_select_id'] = attr.val_select_id_default
                    else:
                        attr_vals['val_bool'] = attr.val_bool_default
                    vals.append((0, 0, attr_vals.copy()))
                projet.update({'of_projet_line_ids': vals})

    # Récupération du site web à la sélection du partenaire
    # Pas de api.onchange parceque crm.lead._onchange_partner_id_values
    def _onchange_partner_id_values(self, partner_id):
        res = super(CrmLead, self)._onchange_partner_id_values(partner_id)

        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)

            res['of_website'] = partner.website
            res['geo_lat'] = partner.geo_lat
            res['geo_lng'] = partner.geo_lng
        return res

    @api.model
    def create(self, vals):
        if not vals.get('partner_id'):
            vals, partner_vals = self._of_extract_partner_values(vals)  # split vals
            partner_vals.update({
                'name': vals.get('contact_name') or vals['name'],
                'type': False,
                'customer': True,
            })

            partner = self.env['res.partner'].create(partner_vals)
#            vals['of_customer_state'] = partner.of_customer_state
            vals['partner_id'] = partner.id
        lead = super(CrmLead, self).create(vals)
        return lead

    @api.multi
    def write(self, vals):
        partner_vals = False
        if len(self._ids) == 1 and vals.get('partner_id', self.partner_id):
            vals, partner_vals = self._of_extract_partner_values(vals)
        super(CrmLead, self).write(vals)
        if partner_vals:
            self.partner_id.write(partner_vals)
        return True

    # Recherche du code postal en mode préfixe
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'zip' and args[pos][1] in ('like', 'ilike') and args[pos][2]:
                args[pos] = ('zip', '=like', args[pos][2]+'%')
            pos += 1
        return super(CrmLead, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.multi
    def action_set_lost(self):
        """ surcharge sans appel à super(), une opportunité perdue n'est pas forcément archivée
            fonction appelée (au moins) depuis le wizard de motif de perte
        """
        for lead in self:
            stage_id = lead._stage_find(domain=[('probability', '=', 0.0), ('on_change', '=', True)])
            lead.write({'stage_id': stage_id.id,
                        'probability': 0,
                        'of_date_cloture': time.strftime(DEFAULT_SERVER_DATE_FORMAT),
                        })
        return True

    @api.multi
    def action_set_won(self):
        res = super(CrmLead, self).action_set_won()
        for lead in self:
            lead.of_date_cloture = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return res

    @api.model
    def get_color_map(self):
        """
        Fonction pour la légende de la vue map
        """
        return {
            'title': u"Prochaine Activité",
            'values': (
                {'label': u'Aucune', 'value': 'gray'},
                {'label': u"Plus d'un mois", 'value': 'blue'},
                {'label': u'Ce mois-ci', 'value': 'orange'},
                {'label': u'En retard', 'value': 'red'},
            )
        }

    @api.model
    def _of_extract_partner_values(self, vals):
        new_vals = vals.copy()
        partner_vals = {}
        for field_name, val in vals.iteritems():
            if field_name not in self._fields:  # don't take vals that are not fields into account
                continue
            field = self._fields[field_name]
            if not getattr(field, 'related'):  # field is not related -> let it be
                continue
            related = field.related
            if related and related[0] == 'partner_id':  # field related to partner_id
                partner_vals['.'.join(related[1:])] = val  # add value to partner_vals
                del new_vals[field_name]  # take value out of new vals
        return new_vals, partner_vals


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    # Retrait des filtres de recherche par défaut dans la vue 'Votre pipeline'
    # Ajout de la vue map. Cette action est appelée depuis le menu 'votre pipeline',
    # l'action xml est appelée en rafraîchissant la page (?!?)
    @api.model
    def action_your_pipeline(self):
        action = super(CrmTeam, self).action_your_pipeline()
        map_view_id = self.env.ref('of_crm.of_crm_map_view').id
        action['views'].insert(2, [map_view_id, 'map'])
        action['context'] = {key: val for key, val in action['context'].iteritems()
                             if not key.startswith('search_default_')}
        return action


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def get_date_updated(self):
        """
        Renvoie la date et l'heure du rendez-vous en heure locale au format JJ/MM/AAAA HH:MM
        """
        self.ensure_one()
        return fields.Datetime.context_timestamp(self, datetime.strptime(self.start, "%Y-%m-%d %H:%M:%S")).\
            strftime("%d/%m/%Y %H:%M")

    def get_meeting_data(self):
        self.ensure_one()
        res = ['start', 'name', 'description', 'location']
        return res
