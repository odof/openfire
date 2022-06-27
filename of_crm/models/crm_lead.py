# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.safe_eval import safe_eval

from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import time
import pytz
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
        cr = self._cr
        cr.execute(
            "SELECT * FROM information_schema.columns WHERE table_name = 'crm_lead' AND column_name = 'of_date_projet'")
        of_date_projet = bool(cr.fetchall())
        res = super(CrmLead, self)._auto_init()
        if not of_date_projet:
            cr.execute("UPDATE crm_lead SET of_date_projet = date_deadline, date_deadline = of_date_cloture")
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
    geo_lat = fields.Float(related="partner_id.geo_lat", readonly=True)
    geo_lng = fields.Float(related="partner_id.geo_lng", readonly=True)
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

    of_activity_ids = fields.One2many(
        comodel_name='of.crm.activity', inverse_name='opportunity_id', string=u"Activités",
        context={'active_test': False})
    of_intervention_ids = fields.One2many(
        comodel_name='of.planning.intervention', inverse_name='opportunity_id', string=u"RDVs d'intervention")
    of_intervention_count = fields.Integer(
        string=u"Nb de RDVs d'intervention", compute='_compute_of_intervention_count')
    of_next_action_activity_id = fields.Many2one(
        comodel_name='of.crm.activity', string=u"Activité nécessitant la prochaine action",
        compute='_compute_of_action_info')
    # store=True car of_date_action est la date de référence pour la vue calendar
    of_date_action = fields.Datetime(
        string=u"Date de la prochaine action", compute='_compute_of_action_info', store=True)
    of_title_action = fields.Char(string=u"Libellé de la prochaine action", compute='_compute_of_action_info')

    of_date_projet = fields.Date(string="Date projet")

    of_check_duplications = fields.Boolean(string=u"Contrôle de doublons ?")

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

    @api.depends('of_intervention_ids')
    @api.multi
    def _compute_of_intervention_count(self):
        for opportunity in self:
            opportunity.of_intervention_count = len(opportunity.of_intervention_ids)

    @api.multi
    def _compute_kanban_state(self):
        for opportunity in self:
            kanban_state = 'grey'
            if opportunity.of_activity_ids.filtered(lambda act: act.is_late):
                kanban_state = 'red'
            elif opportunity.of_activity_ids.filtered(lambda act: act.state == 'planned'):
                kanban_state = 'green'
            opportunity.kanban_state = kanban_state

    @api.multi
    def _compute_of_action_info(self):
        for opportunity in self:
            if opportunity.of_activity_ids.filtered(lambda act: act.state == 'planned'):
                next_activity = opportunity.of_activity_ids.filtered(lambda act: act.state == 'planned')[-1]
                opportunity.of_next_action_activity_id = next_activity
                opportunity.of_date_action = next_activity.date
                opportunity.of_title_action = next_activity.title
            else:
                opportunity.of_next_action_activity_id = False
                opportunity.of_date_action = False
                opportunity.of_title_action = False

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
        return res

    def _of_get_fields_recompute_auto_activities(self):
        """Helper function to return the list of fields that will trigger the recompute
        the deadline date of activities"""
        return ['of_date_projet', 'date_deadline']

    @api.multi
    def _of_update_deadline_date_activities(self, activity_fields=None):
        """Recomputes the deadline date of activities linked to the Sale.
        :param activity_fields: The list of fields that are updated to filter activities to update
        :type activity_fields: list
        """
        if activity_fields is None:
            activity_fields = []

        field_name = {
            'of_date_projet': 'project_date',
            'date_deadline': 'decision_date'
        }
        activities_filter = [field_name.get(af) for af in activity_fields if field_name.get(af)]
        for crm in self:
            for crm_activity in crm.of_activity_ids.filtered(
                    lambda ca:
                    ca.state == 'planned' and ca.type_id and
                    ca.type_id.of_compute_date in activities_filter and
                    ca.type_id.of_automatic_recompute):
                crm_activity.date = crm_activity._of_get_crm_activity_date_deadline()

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
            vals['of_check_duplications'] = True
        lead = super(CrmLead, self).create(vals)

        # Check if the dict of values contains fields that will trigger the recompute of the deadline date of
        # the activities.
        activity_fields = filter(
            lambda f: f, [f in self._of_get_fields_recompute_auto_activities() and f for f in vals.keys()])
        if activity_fields:
            lead._of_update_deadline_date_activities(activity_fields)

        return lead

    @api.multi
    def write(self, vals):
        partner_vals = False
        if len(self._ids) == 1 and vals.get('partner_id', self.partner_id):
            vals, partner_vals = self._of_extract_partner_values(vals)
        res = super(CrmLead, self).write(vals)
        if partner_vals:
            self.partner_id.write(partner_vals)
        if vals.get('stage_id') and not self._context.get('crm_stage_auto_update'):
            stage = self.env['crm.stage'].browse(vals.get('stage_id'))
            if stage.of_manual_activity_id:
                # Mise à jour de l'état manuelle -> création d'une activité
                for rec in self:
                    self.env['of.crm.activity'].create(
                        {'opportunity_id': rec.id,
                         'title': stage.of_manual_activity_id.name,
                         'type_id': stage.of_manual_activity_id.id,
                         'date': fields.Datetime.from_string(fields.Datetime.now()[:-2] + '00'),
                         'user_id': self.env.user.id,
                         'vendor_id': rec.user_id and rec.user_id.id or self.env.user.id,
                         'state': 'planned'}
                    )
        if 'active' in vals:
            self.mapped('of_activity_ids').write({'active': vals['active']})
        # Check if the dict of values contains fields that will trigger the recompute of the deadline date of
        # the activities.
        activity_fields = filter(
            lambda f: f, [f in self._of_get_fields_recompute_auto_activities() and f for f in vals.keys()])
        if activity_fields:
            self._of_update_deadline_date_activities(activity_fields)
        return res

    # Recherche du code postal en mode préfixe
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'zip' and args[pos][1] in ('like', 'ilike') and args[pos][2]:
                args[pos] = ('zip', '=like', args[pos][2] + '%')
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

    @api.multi
    def action_view_interventions(self):
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            context.update({
                'default_address_id': self.partner_id and self.partner_id.id or False,
                'default_opportunity_id': self.id,
            })
            if self.of_intervention_ids:
                context['force_date_start'] = self.of_intervention_ids[-1].date_date
                context['search_default_opportunity_id'] = self.id
            action['context'] = str(context)
        action = self.mapped('of_intervention_ids').get_action_views(self, action)
        return action

    @api.multi
    def action_view_activity(self):
        action = self.env.ref('of_crm.of_crm_activity_schedule_action').read()[0]
        if len(self._ids) == 1:
            context = safe_eval(action['context'])
            if self.of_next_action_activity_id:
                action['res_id'] = self.of_next_action_activity_id.id
                context.update({
                    'res_id': self.of_next_action_activity_id.id,
                    'active_ids': self.of_next_action_activity_id.ids,
                })
            else:
                context.update({
                    'default_opportunity_id': self.id,
                })
            action['context'] = str(context)
            action['target'] = 'new'
        return action

    @api.model
    def retrieve_sales_dashboard(self):
        result = super(CrmLead, self).retrieve_sales_dashboard()

        result['activity']['today'] = 0
        result['activity']['overdue'] = 0
        result['activity']['next_7_days'] = 0
        result['done']['this_month'] = 0
        result['done']['last_month'] = 0

        today = fields.Date.from_string(fields.Date.context_today(self))

        next_activities = self.env['of.crm.activity'].search([('state', '=', 'planned'), ('vendor_id', '=', self._uid)])

        for activity in next_activities:
            if activity.date:
                date_action = fields.Date.from_string(activity.date)
                if date_action == today:
                    result['activity']['today'] += 1
                if today <= date_action <= today + timedelta(days=7):
                    result['activity']['next_7_days'] += 1
                if activity.is_late:
                    result['activity']['overdue'] += 1

        activities_done = self.env['of.crm.activity'].\
            search([('state', '=', 'done'), ('vendor_id', '=', self._uid)])

        for activity in activities_done:
            if activity.date:
                date_act = fields.Date.from_string(activity.date)
                if today.replace(day=1) <= date_act <= today:
                    result['done']['this_month'] += 1
                elif today + relativedelta(months=-1, day=1) <= date_act < today.replace(day=1):
                    result['done']['last_month'] += 1

        return result

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

    @api.depends('order_ids')
    def _compute_sale_amount_total(self):
        for lead in self:
            total = 0.0
            nbr = 0
            company_currency = lead.company_currency or self.env.user.company_id.currency_id
            for order in lead.order_ids:
                if order.state in ('draft', 'sent', 'sale', 'done'):
                    nbr += 1
                if order.state not in ('draft', 'sent', 'cancel'):
                    total += order.currency_id.compute(order.amount_untaxed, company_currency)
            lead.sale_amount_total = total
            lead.sale_number = nbr


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


class CRMStage(models.Model):
    _inherit = 'crm.stage'

    of_auto_model_name = fields.Selection(
        selection=[('sale.order', u"Bon de commande"),
                   ('of.planning.intervention', u"RDV d'intervention")], string=u"Modèle")
    of_auto_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string=u"Champ")
    of_auto_comparison_code = fields.Char(string=u"Code de comparaison")
    of_manual_activity_id = fields.Many2one(
        comodel_name='crm.activity', string=u"Activité à créer en cas de mise à jour manuelle")


class OFCRMActivity(models.Model):
    _name = 'of.crm.activity'
    _inherit = ['mail.thread']
    _description = "OF Activité de CRM"
    _rec_name = 'title'
    _order = 'date desc'

    @api.model_cr_context
    def _auto_init(self):
        """
        On récupère les prochaines activités programmées
        """
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.tables WHERE table_name = '%s'" % (self._table,))
        exists = bool(cr.fetchall())
        res = super(OFCRMActivity, self)._auto_init()
        if not exists:
            tz = pytz.timezone('Europe/Paris')
            opportunities = self.env['crm.lead'].search([('next_activity_id', '!=', False)])
            for opportunity in opportunities:
                self.create({'opportunity_id': opportunity.id,
                             'title': opportunity.next_activity_id.name,
                             'type_id': opportunity.next_activity_id.id,
                             'date': tz.localize(fields.Datetime.
                                                 from_string((opportunity.date_action or fields.Date.today()) +
                                                             ' 09:00:00')).astimezone(pytz.utc),
                             'description': opportunity.title_action,
                             'user_id': SUPERUSER_ID,
                             'vendor_id': opportunity.user_id and opportunity.user_id.id or SUPERUSER_ID,
                             'state': 'planned'})
        return res

    active = fields.Boolean(string='Actif', default=True)
    title = fields.Char(string=u"Résumé", required=True, track_visibility="always")
    opportunity_id = fields.Many2one(comodel_name='crm.lead', string=u"Opportunité", required=True, ondelete='cascade')
    type_id = fields.Many2one(
        comodel_name='crm.activity', string="Activity type", required=True,
        domain=['|', ('of_object', '=', 'opportunity'), ('of_object', '=', False)])
    date = fields.Datetime(string=u"Date", required=True, track_visibility="always")
    state = fields.Selection(
        selection=[('planned', u"Planifiée"),
                   ('done', u"Réalisée"),
                   ('canceled', u"Annulée")], string=u"État", required=True, default='planned',
        track_visibility="onchange")
    user_id = fields.Many2one(
        comodel_name='res.users', string=u"Auteur", required=True, default=lambda self: self.env.user)
    vendor_id = fields.Many2one(comodel_name='res.users', string=u"Commercial", required=True)
    description = fields.Text(string=u"Description")
    report = fields.Text(string=u"Compte-rendu", track_visibility="onchange")
    cancel_reason = fields.Text(string=u"Raison d'annulation", track_visibility="onchange")
    partner_id = fields.Many2one(related='opportunity_id.partner_id', string=u"Client", readonly=True)
    phone = fields.Char(related='opportunity_id.phone', string=u"Téléphone", readonly=True)
    mobile = fields.Char(related='opportunity_id.mobile', string=u"Mobile", readonly=True)
    email = fields.Char(related='opportunity_id.email_from', string=u"Courriel", readonly=True)
    is_late = fields.Boolean(string=u"Activité en retard", compute="_compute_is_late", search="_search_is_late")
    # Couleurs
    of_color_ft = fields.Char(string=u"Couleur de texte", compute='_compute_custom_colors')
    of_color_bg = fields.Char(string=u"Couleur de fond", compute='_compute_custom_colors')

    @api.multi
    def _compute_is_late(self):
        for activity in self:
            if activity.state == 'planned' and activity.date < fields.Datetime.now():
                activity.is_late = True
            else:
                activity.is_late = False

    @api.model
    def _search_is_late(self, operator, value):
        late_activities = self.env['of.crm.activity'].search(
            [('state', '=', 'planned'), ('date', '<', fields.Datetime.now())])
        if operator == '=':
            return [('id', 'in', late_activities.ids)]
        else:
            return [('id', 'not in', late_activities.ids)]

    @api.onchange('opportunity_id')
    def _onchange_opportunity_id(self):
        if self.opportunity_id:
            self.vendor_id = self.opportunity_id.user_id

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id:
            if not self.title:
                self.title = self.type_id.name
            self.date = self._of_get_crm_activity_date_deadline()
            self.description = self.type_id.description
            if self.type_id.of_user_id:
                self.vendor_id = self.type_id.of_user_id

    @api.multi
    def _compute_custom_colors(self):
        for activity in self:
            if activity.vendor_id:
                activity.of_color_ft = activity.vendor_id.of_color_ft
                activity.of_color_bg = activity.vendor_id.of_color_bg
            else:
                activity.of_color_ft = "#0D0D0D"
                activity.of_color_bg = "#F0F0F0"

    @api.multi
    def _of_get_crm_activity_date_deadline(self):
        self.ensure_one()

        if not self.type_id:
            return False

        compute_date = self.type_id.of_compute_date
        days = self.type_id.days
        field_name = {
            'project_date': 'of_date_projet',
            'decision_date': 'date_deadline'
        }
        crm_field = field_name.get(compute_date)
        if crm_field:
            ddate = getattr(self.opportunity_id, crm_field)
            ddate = fields.Datetime.from_string(ddate)
        else:
            ddate = datetime.now()
        if ddate:
            delta = timedelta(days=days)
            return ddate + delta
        return False

    @api.multi
    def message_track(self, tracked_fields, initial_values):
        return super(OFCRMActivity, self.with_context(to_lead=True)).message_track(tracked_fields, initial_values)

    @api.multi
    def message_post(self, body='', subject=None, message_type='notification',
                     subtype=None, parent_id=False, attachments=None,
                     content_subtype='html', **kwargs):
        self.ensure_one()
        if self.opportunity_id and self._context.get("to_lead"):
            self.opportunity_id.message_post(body=body, subject=subject, message_type=message_type,
                                             subtype=subtype, parent_id=parent_id, attachments=attachments,
                                             content_subtype=content_subtype, **kwargs)
        return super(OFCRMActivity, self).message_post(body=body, subject=subject, message_type=message_type,
                                                       subtype=subtype, parent_id=parent_id, attachments=attachments,
                                                       content_subtype=content_subtype, **kwargs)


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
