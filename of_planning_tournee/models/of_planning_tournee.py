# -*- encoding: utf-8 -*-

from odoo import api, models, fields, registry
from odoo.api import Environment
from odoo.exceptions import ValidationError

import math
from math import asin, sin, cos, sqrt

def get_id(cr, uid, id, champ=False, table=False):
    pre = ""
    if table and champ:
        try:
            cr.execute("SELECT id from " + str(table) + " WHERE " + str(champ) + "='" + str(id) + "'")
            pre = cr.fetchone()[0]
        except:
            pass
    return pre

def get_ch(cr, uid, id, champ=False, table=False):
    pre = ""
    if table and champ:
        try:
            cr.execute("SELECT " + str(champ) + " from " + str(table) + " WHERE id='" + str(id) + "'")
            pre = cr.fetchone()[0]
        except:
            pass
    return pre

def distance_points(lat1, lon1, lat2, lon2):
    u"""
    Retourne la distance entre deux points en Km, à vol d'oiseau
    @param *: Coordonnées gps en degrés
    """
    lat1, lon1, lat2, lon2 = [math.radians(v) for v in (lat1, lon1, lat2, lon2)]
    return 2*asin(sqrt((sin((lat1-lat2)/2)) ** 2 + cos(lat1)*cos(lat2)*(sin((lon1-lon2)/2)) ** 2)) * 6366

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    @api.multi
    @api.depends('equipe_id', 'date', 'tournee_id.date', 'tournee_id.equipe_id')
    def _compute_tournee_id(self):
        tournee_obj = self.env['of.planning.tournee']
        for intervention in self:
            tournee = tournee_obj.search([('equipe_id', '=', intervention.equipe_id.id), ('date', '=', intervention.date[:10])], limit=1)
            intervention.tournee_id = tournee

    @api.depends('equipe_id', 'date', 'date_deadline')
    def _compute_tournee_is_complet(self):
        # Récupération des valeurs AVANT la modification
        tournee_ids = []
        with registry(self._cr.dbname).cursor() as cr:
            self = self.with_env(self.env(cr=cr))
            old_env = Environment(self._cr, self._uid, self._context)
            for intervention in old_env['of.planning.intervention'].browse(self._ids):
                if intervention.tournee_id:
                    tournee_ids.append(intervention.tournee_id)
        for intervention in self:
            if intervention.tournee_id:
                tournee_ids.append(intervention.tournee_id)
        tournees = self.env['of.planning.tournee'].browse(list(set(tournee_ids)))
        tournees._compute_is_complet()

    tournee_id = fields.Many2one('of.planning.tournee', compute='_compute_tournee_id', string='Planification')
    partner_city = fields.Char(related='address_id.city', store=True)

    @api.multi
    def create_tournee(self):
        self.ensure_one()
        tournee_obj = self.env['of.planning.tournee']
        # if self.tache_id.category_id.type_planning_intervention != 'tournee':
        #     return False
        date_intervention = self.date
        date_jour = isinstance(date_intervention, basestring) and date_intervention[:10] or date_intervention.strftime('%Y-%m-%d')
        address = self.address_id
        # ville = address.ville or address
        ville = address
        country = address.country_id
        tournee_data = {
            'date'       : date_jour,
            'equipe_id'  : self.equipe_id.id,
            'epi_lat'    : ville.geo_lat,
            'epi_lon'    : ville.geo_lng,
            'adr_id'     : address.id,
            # 'ville'      : address.ville and address.ville.id,
            'zip'        : ville.zip,
            'city'       : ville.city,
            'country_id' : country and country.id,
            'is_bloque'  : False,
            'is_confirme': False
        }
        return tournee_obj.create(tournee_data)

    @api.model
    def remove_tournee(self, date, equipe_id):
        date = isinstance(date, basestring) and date[:10] or date.strftime('%Y-%m-%d')
        planning_intervention_ids = self.search([('date', '>=', date), ('date', '<=', date), ('equipe_id', '=', equipe_id)])
        if planning_intervention_ids:
            # Il existe encore des plannings pour la tournee, on ne la supprime pas
            return True

        planning_tournee_obj = self.env['of.planning.tournee']
        plannings_tournee = planning_tournee_obj.search([('date', '=', date), ('equipe_id', '=', equipe_id),
                                                         ('is_bloque', '=', False), ('is_confirme', '=', False)])
        plannings_tournee.unlink()

    @api.model
    def create(self, vals):
        planning_tournee_obj = self.env['of.planning.tournee']

        # On verifie que la tournee n'est pas deja complete ou bloquee
        date_jour = isinstance(vals['date'], basestring) and vals['date'][:10] or vals['date'].strftime('%Y-%m-%d')

        planning_tournee_ids = planning_tournee_obj.search([('date', '=', date_jour),
                                                            ('equipe_id', '=', vals['equipe_id']),
                                                            ('is_bloque', '=', True)])
        if planning_tournee_ids:
            raise ValidationError(u'La tournée de cette équipe est bloquée')

        intervention = super(OfPlanningIntervention, self).create(vals)
        planning_tournee_ids = planning_tournee_obj.search([('date', '=', date_jour),
                                                            ('equipe_id', '=', vals['equipe_id'])])
        if not planning_tournee_ids:
            intervention.create_tournee()
        return intervention

    @api.multi
    def write(self, vals):
        planning_tournee_obj = self.env['of.planning.tournee']

        interventions = []
        if 'date' in vals or 'equipe_id' in vals:
            for intervention in self:
                date = vals.get('date', intervention.date)
                equipe_id = vals.get('equipe_id', intervention.equipe_id.id)

                date_jour = isinstance(date, basestring) and date[:10] or date.strftime('%Y-%m-%d')
                interventions.append((intervention, date_jour, equipe_id, intervention.date, intervention.equipe_id.id))
                planning_tournee_ids = planning_tournee_obj.search([('date', '=', date_jour),
                                                                    ('equipe_id', '=', equipe_id),
                                                                    ('is_bloque', '=', True)])
                if planning_tournee_ids:
                    raise ValidationError(u'La tournée de cette équipe est bloquée')
        super(OfPlanningIntervention, self).write(vals)

        for intervention, date_jour, equipe_id, date_prec, equipe_prec in interventions:
            planning_tournee_ids = planning_tournee_obj.search([('date', '=', date_jour), ('equipe_id', '=', equipe_id)])
            if not planning_tournee_ids:
                intervention.create_tournee()
            self.remove_tournee(date_prec, equipe_prec)
        return True

    @api.multi
    def unlink(self):
        interventions = []
        for intervention in self:
            date = intervention.date
            date_jour = isinstance(date, basestring) and date[:10] or date.strftime('%Y-%m-%d')
            interventions.append((date_jour, intervention.equipe_id.id))
        super(OfPlanningIntervention, self).unlink()
        for date, equipe_id in interventions:
            self.remove_tournee(date, equipe_id)
        return True

    @api.multi
    def _calc_new_description(self):
        self.ensure_one()

        tache = self.tache_id
        for service in self.address_id.service_address_ids:
            if service.tache_id == tache:
                infos = (
                    self.description,
                    tache.name,
                    # service.template_id and service.template_id.name,
                    service.note
                )
                res = [info for info in infos if info]
                self.description = "\n".join(res)

    @api.onchange('address_id')
    def _onchange_address_id(self):
        super(OfPlanningIntervention, self)._onchange_address_id()
        if self.address_id and self.tache_id:
            self._calc_new_description()

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        super(OfPlanningIntervention, self)._onchange_tache_id()
        if self.partner_id and self.tache_id:
            self._calc_new_description()


class OfPlanningEquipe(models.Model):
    _inherit = "of.planning.equipe"

    address_id = fields.Many2one('res.partner', string='Adresse')
    geo_lat = fields.Float(related='address_id.geo_lat')
    geo_lng = fields.Float(related='address_id.geo_lng')

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        if self.employee_ids:
            self.address_id = self.employee_ids[0].address_home_id


# class OfParamDocs(models.Model):
#     _name = 'of.param.docs'
#     _description = u'Paramétrage des documents'
#
#     _columns = {
#         'name': fields.char('Nom de document', size=128, required=True),
#         'short_name': fields.char('ID', size=16, required=True),
#         'model': fields.selection([('sale.order', 'Commande Client'), ('account.invoice', 'Facture Client'), ('of.planning.intervention', "Planning d'intervention")],
#                                   'Domaine', required=True),
#         'report_template': fields.many2one('ir.actions.report.xml', 'Rapport'),
#         'mail_template': fields.many2one('mail.template', u'Mod\u00E8le de courrier'),
#         'doc_type': fields.selection([('openfire', 'OpenFire'), ('mail', 'Courrier'), ('acrobat', 'Acrobat')], 'Type', readonly=True),
#         'default_doc': fields.boolean(u'Défaut'),
#         'planning_res_id': fields.many2one('of.planning.res', u'Tournée'),
#     }
#
#     def onchange_report(self, cr, uid, ids, report_template):
#         report_obj = self.pool['ir.actions.report.xml']
#
#         if report_template:
#             name = report_obj.browse(cr, uid, report_template).name
#             if name != 'Attestation TVA':
#                 doc_type = 'openfire'
#             else:
#                 doc_type = 'acrobat'
#             return {'value': {'mail_template': False, 'name': name, 'doc_type': doc_type}}
#
#     def onchange_mail(self, cr, uid, ids, mail_template):
#         mail_tmpl_obj = self.pool['mail.template']
#
#         if mail_template:
#             name = mail_tmpl_obj.browse(cr, uid, mail_template).name
#             return {'value': {'report_template': False, 'name': name, 'doc_type': 'mail'}}
#
#     def create(self, cr, uid, data, context={}):
#         doc_type = False
#         report_template = False
#         mail_template = False
#         if 'report_template' in data.keys():
#             if data['report_template']:
#                 report_template = data['report_template']
#         if 'mail_template' in data.keys():
#             if data['mail_template']:
#                 mail_template = data['mail_template']
#         if report_template:
#             if self.pool['ir.actions.report.xml'].browse(cr, uid, report_template).name == 'Attestation TVA':
#                 doc_type = 'acrobat'
#             else:
#                 doc_type = 'openfire'
#         elif mail_template:
#             doc_type = 'mail'
#
#         if doc_type:
#             data['doc_type'] = doc_type
#         return super(of_param_docs, self).create(cr, uid, data, context)
#
#     def write(self, cr, uid, ids, data, context={}):
#         doc_type = False
#         report_template = False
#         mail_template = False
#         if 'report_template' in data.keys():
#             if data['report_template']:
#                 report_template = data['report_template']
#         if 'mail_template' in data.keys():
#             if data['mail_template']:
#                 mail_template = data['mail_template']
#         if report_template:
#             if self.pool['ir.actions.report.xml'].browse(cr, uid, report_template).name == 'Attestation TVA':
#                 doc_type = 'acrobat'
#             else:
#                 doc_type = 'openfire'
#         elif mail_template:
#             doc_type = 'mail'
#         if doc_type:
#             data['doc_type'] = doc_type
#         return super(of_param_docs, self).write(cr, uid, ids, data, context)
#
# of_param_docs()


class OfPlanningTournee(models.Model):
    _name = "of.planning.tournee"
    _description = "Tournée"

    @api.multi
    @api.depends('equipe_id', 'date', 'is_bloque',
                 'equipe_id.hor_md', 'equipe_id.hor_mf', 'equipe_id.hor_ad', 'equipe_id.hor_af')
    def _compute_is_complet(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        intervention_obj = self.env['of.planning.intervention']
        for tournee in self:
            if tournee.is_bloque:
                tournee.is_complet = False
                continue

            equipe = tournee.equipe_id

            interventions = intervention_obj.search([
                ('equipe_id', '=', equipe.id),
                ('date', '<=', tournee.date),
                ('date_deadline', '>=', tournee.date),
                ('state', 'in', ('draft', 'confirm'))
            ], order="date")
            if not interventions:
                tournee.is_complet = False
                continue

            date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(tournee.date))
            start_end_list = [
                (0, equipe.hor_md),
                (equipe.hor_mf, equipe.hor_ad),
                (equipe.hor_af, 24)
            ]

            for intervention in interventions:
                start_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention.date))
                if start_local.day != date_local.day:
                    start_flo = equipe.hor_md
                else:
                    start_flo = (start_local.hour +
                                 start_local.minute / 60 +
                                 start_local.second / 3600)

                end_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention.date_deadline))
                if end_local.day != date_local.day:
                    end_flo = equipe.hor_af
                else:
                    end_flo = (start_local.hour +
                               start_local.minute / 60 +
                               start_local.second / 3600)

                start_end_list.append((start_flo, end_flo))
            start_end_list.sort()

            is_complet = True
            last_end = 0
            for s, e in start_end_list:
                if s - last_end > 0:
                    is_complet = False
                    break
                if e > last_end:
                    last_end = e
            tournee.is_complet = is_complet

    @api.depends('date')
    def _get_jour(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        for tournee in self:
            jour = ""
            if tournee.date:
                date_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(tournee.date))
                jour = date_local.strftime("%A").capitalize()
            tournee.date_jour = jour

#     def _get_doc_name(self, cr, uid, ids, field, args, context=None):
#         ids = isinstance(ids, int or long) and [ids] or ids
#         doc_names = {}
#         for res in self.browse(cr, uid, ids):
#             names = ''
#             if res.docs:
#                 for doc in res.docs:
#                     names += doc.short_name + ' '
#             names = names.rstrip(' ')
#             doc_names[res.id] = names
#         return doc_names
#
#     def _set_doc_name(self, cr, uid, ids, name, value, arg, context):
#         ids = isinstance(ids, int or long) and [ids] or ids
#         param_docs_obj = self.pool['of.param.docs']
#         param_docs = [(5, 0)]
#         if value:
#             short_name_list = value.split(' ')
#             param_docs_ids = []
#             if len(short_name_list):
#                 param_docs_ids = param_docs_obj.search(cr, uid, [('short_name', 'in', tuple(short_name_list))])
#             for param_doc in param_docs_ids:
#                 param_docs.append((4, param_doc))
#         for res in self.browse(cr, uid, ids):
#             res.write({'docs': param_docs})
#
#     def _get_res(self, cr, uid, ids, context={}):
#         ids = isinstance(ids, int or long) and [ids] or ids
#         result = {}
#         for param_docs in self.pool['of.param.docs'].browse(cr, uid, ids, context=context):
#             result[param_docs.planning_res_id.id] = True
#         return result.keys()
#
#     def _default_docs(self, cr, uid, contex={}):
#         param_doc_obj = self.pool['of.param.docs']
#         docs = [(5, 0)]
#         default_doc_ids = param_doc_obj.search(cr, uid, [('default_doc', '=', True)])
#         for dd in default_doc_ids:
#             docs.append((4, dd))
#         return docs
#
#     def _default_docs_name(self, cr, uid, contex={}):
#         param_doc_obj = self.pool['of.param.docs']
#         doc_names = ''
#         default_doc_ids = param_doc_obj.search(cr, uid, [('default_doc', '=', True)])
#         for dd in param_doc_obj.browse(cr, uid, default_doc_ids):
#             doc_names += dd.short_name + ' '
#         doc_names = doc_names.rstrip(' ')
#         return doc_names

    date = fields.Date(string='Date', required=True)
    date_jour = fields.Char(compute="_get_jour", string="Jour")
    equipe_id = fields.Many2one('of.planning.equipe', string=u'Équipe', required=True)
    epi_lat = fields.Float(string=u'Épicentre Lat', digits=(12, 12), required=True)
    epi_lon = fields.Float(string=u'Épicentre Lon', digits=(12, 12), required=True)

    zip_id = fields.Many2one('res.better.zip', 'Ville')
    distance = fields.Float(string='Eloignement (km)', digits=(12, 4), required=True, default=20.0)
    is_complet = fields.Boolean(compute="_compute_is_complet", string='Complet', store=True)
    is_bloque = fields.Boolean(string=u'Bloqué', help=u'Journée bloquée : ne sera pas proposée à la planification')
    is_confirme = fields.Boolean(string=u'Confirmé', default=True, help=u'Une tournée non confirmée sera supprimée si on lui retire ses rendez-vous')

    @api.multi
    def _get_dummy_fields(self):
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')
        for tournee in self:
            d = fields.Date.context_today(self)
            tournee.date_min = d
            tournee.date_max = d

#    date_min = fields.Date("Date min", compute='lambda self:for tournee in self:tournee.date_min=fields.Date.context_today(self)')
#    date_max = fields.Date("Date max", compute='lambda self:for tournee in self:tournee.date_max=fields.Date.context_today(self)')

    date_min = fields.Date(related="date", string="Date min")
    date_max = fields.Date(related="date", string="Date max")

#     docs = fields.One2many('of.param.docs', 'planning_res_id', 'Documents')
#     docs_name = fields.function(_get_doc_name, fnct_inv=_set_doc_name, string='Documents', type='char', select=True,
#                                   store={'of.planning.res': (lambda self, cr, uid, ids, c={}: ids, ['docs'], 20),
#                                          'of.param.docs': (_get_res, ['short_name'], 20)})
#     _defaults = {
#         'docs'       : _default_docs,
#         'docs_name'  : _default_docs_name,
#     }

    _sql_constraints = [
        ('date_equipe_uniq', 'unique (date,equipe_id)', u"Il ne peut exister qu'une tournée par équipe pour un jour donné")
    ]

    _rec_name = 'date'
    _order = 'date'

    @api.onchange('zip_id')
    def _onchange_zip_id(self):
        if self.zip_id:
            self.epi_lat = self.zip_id.geo_lat
            self.epi_lon = self.zip_id.geo_lng

    @api.model
    def create(self, vals):
        intervention_obj = self.env['of.planning.intervention']

        if vals.get('is_bloque'):
            if intervention_obj.search([('date', '>=', vals['date']), ('date', '<=', vals['date']),
                                        ('state', 'in', ('draft', 'confirm', 'done')),
                                        ('equipe_id', '=', vals['equipe_id'])]):
                raise ValidationError(u'Il existe déjà les interventions dans la journée de cette équipe')
        return super(OfPlanningTournee, self).create(vals)

    @api.multi
    def write(self, vals):
        intervention_obj = self.env['of.planning.intervention']

        for tournee in self:
            if vals.get('is_bloque', tournee.is_bloque):
                date_intervention = vals.get('date', tournee.date)
                equipe_id = vals.get('equipe_id', tournee.equipe_id.id)
                if intervention_obj.search([('date', '>=', date_intervention), ('date', '<=', date_intervention),
                                            ('state', 'in', ('draft', 'confirm', 'done')),
                                            ('equipe_id', '=', equipe_id)]):
                    raise ValidationError(u'Il existe déjà les interventions dans la journée de cette équipe')
        return super(OfPlanningTournee, self).write(vals)

    @api.multi
    def open_planification(self):
        self.ensure_one()
        plan_obj = self.env['of.tournee.planification']

        planif = plan_obj.create({
            'tournee_id'       : self.id,
            'distance_add'     : self.distance + 10.0,
            'plan_partner_ids' : plan_obj._get_partner_ids(self),
            'plan_planning_ids': plan_obj._get_planning_ids(self),
        })
        return planif._get_show_action()

class OfService(models.Model):
    _inherit = 'of.service'

    def _get_color(self):
        u""" COULEURS :
        gris : Service dont l'adresse n'a pas de coordonnées GPS
        rouge : Service dont la date de dernière intervention est inférieure à la date courante (ou à self._context.get('date_next_max'))
        bleu : Service dont le dernier rendez-vous est planifié hors tournée
        noir : Autres services
        """
        date_next_max = self._context.get('date_next_max') or fields.Date.today()

        for service in self:
            if not (service.address_id.geo_lat or service.address_id.geo_lng):
                service.color = 'gray'
            elif service.date_next <= date_next_max:
                service.color = 'red'
            elif service.planning_ids and not service.planning_ids[0].tournee_id:
                service.color = 'blue'
            else:
                service.color = 'black'
