# -*- encoding: utf-8 -*-

from odoo import api, models, fields, registry
from odoo.api import Environment
from odoo.exceptions import UserError, ValidationError

import math
from math import asin, sin, cos, sqrt

def get_id(cr, uid, id, champ=False, table=False):
    try:
        if table and champ:
            cr.execute("SELECT id from " + str(table) + " WHERE " + str(champ) + "='" + str(id) + "'")
            pre = cr.fetchone()[0]
        else: pre = ""
    except:
        pre = ""
    return pre

def get_ch(cr, uid, id, champ=False, table=False):
    try:
        if table and champ:
            cr.execute("SELECT " + str(champ) + " from " + str(table) + " WHERE id='" + str(id) + "'")
            pre = cr.fetchone()[0]
        else: pre = ""
    except:
        pre = ""
    return pre

def distance_points(lat1, lon1, lat2, lon2):
    u"""
    Retourne la distance entre deux points en Km, à vol d'oiseau
    @param *: Coordonnées gps en degrés
    """
    lat1,lon1,lat2,lon2 = [math.radians(v) for v in (lat1, lon1, lat2, lon2)]
    return 2*asin(sqrt((sin((lat1-lat2)/2)) ** 2 + cos(lat1)*cos(lat2)*(sin((lon1-lon2)/2)) ** 2)) * 6366

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    @api.multi
    @api.depends('equipe_id','date','tournee_id.date','tournee_id.equipe_id')
    def _compute_tournee_id(self):
        tournee_obj = self.env['of.planning.tournee']
        for intervention in self:
            tournee = tournee_obj.search([('equipe_id', '=', intervention.equipe_id.id), ('date', '=', intervention.date[:10])], limit=1)
            intervention.planning_tournee_id = tournee and tournee._ids[0] or False

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

#     @api.multi
#     @api.depends('equipe_id','date')
#     def _get_partner_address(self):
#         for intervention in self:
#             intervention.partner_address_id = intervention.partner_id and intervention.partner_id.address_get(['delivery'])['delivery'] or False

    tournee_id = fields.Many2one('of.planning.tournee', compute='_compute_tournee_id', string='Planification')
#     partner_address_id = fields.Many2one('res.partner', compute='_get_partner', string='Ville')
    partner_city = fields.Char(related='address_id.city', store=True)

    @api.multi
    def create_tournee(self):
        self.ensure_one()
        tournee_obj = self.env['of.planning.tournee']
#        if self.tache_id.category_id.type_planning_intervention != 'tournee':
#            return False
        date_intervention = self.date
        date_jour = isinstance(date_intervention, basestring) and date_intervention[:10] or date_intervention.strftime('%Y-%m-%d')
        address = self.address_id
#        ville = address.ville or address
        ville = address
        country = address.country_id
        tournee_data = {
            'date'       : date_jour,
            'equipe_id'  : self.equipe_id.id,
            'epi_lat'    : ville.geo_lat,
            'epi_lon'    : ville.geo_lng,
            'adr_id'     : address.id,
#            'ville'      : address.ville and address.ville.id,
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
        planning_intervention_ids = self.search([('date','>=',date), ('date','<=',date), ('equipe_id','=',equipe_id)])
        if planning_intervention_ids:
            # Il existe encore des plannings pour la tournee, on ne la supprime pas
            return True

        planning_tournee_obj = self.env['of.planning.tournee']
        plannings_tournee = planning_tournee_obj.search([('date','=',date), ('equipe_id','=',equipe_id),
                                                         ('is_bloque','=',False), ('is_confirme','=',False)])
        plannings_tournee.unlink()

    @api.model
    def create(self, vals):
        planning_tournee_obj = self.env['of.planning.tournee']

        # On verifie que la tournee n'est pas deja complete ou bloquee
        date_jour = isinstance(vals['date'], basestring) and vals['date'][:10] or vals['date'].strftime('%Y-%m-%d')

        planning_tournee_ids = planning_tournee_obj.search([('date','=',date_jour),
                                                            ('equipe_id','=',vals['equipe_id']),
                                                            ('is_bloque','=',True)])
        if planning_tournee_ids:
            raise ValidationError(u'La tournée de cette équipe est bloquée')

        intervention = super(OfPlanningIntervention, self).create(vals)
        planning_tournee_ids = planning_tournee_obj.search([('date','=',date_jour),
                                                            ('equipe_id','=',vals['equipe_id'])])
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
                planning_tournee_ids = planning_tournee_obj.search([('date','=',date_jour),
                                                                    ('equipe_id','=',equipe_id),
                                                                    ('is_bloque','=',True)])
                if planning_tournee_ids:
                    raise ValidationError(u'La tournée de cette équipe est bloquée')
        super(OfPlanningIntervention, self).write(vals)

        for intervention, date_jour, equipe_id, date_prec, equipe_prec in interventions:
            planning_tournee_ids = planning_tournee_obj.search([('date','=',date_jour), ('equipe_id','=',equipe_id)])
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
        for service in self.address_id.service_ids:
            if service.tache_id == tache:
                infos = (
                    self.description,
                    tache.name,
                    service.template_id and service.template_id.name,
                    service.note
                )
                res = [info for info in infos if info]
                self.description = "\n".join(res)

    @api.onchange('address_id')
    def _onchange_address_id(self):
        super(OfPlanningIntervention, self)._onchange_partner_id()
        if self.address_id and self.tache_id:
            self._calc_new_description()

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        super(OfPlanningIntervention, self).onchange_tache()
        if self.partner_id and self.tache_id:
            self._calc_new_description()


class OfPlanningEquipe(models.Model):
    _inherit = "of.planning.equipe"

    address_id = fields.Many2one('res.partner', string='Adresse')

#     city_id = fields.Many2one('of.commune', string='CP & Ville')
#     geo_lat = fields.Float('GPS Lat', digits=(12, 12))
#     geo_lng = fields.Float('GPS Lon', digits=(12, 12))
#     country_id = fields.Many2one('res.country', 'Pays')
#     street = fields.Char('Rue', size=128)
#     street2 = fields.Char('Rue (suite)', size=128)
#     zip = fields.Char('Code Postal', change_default=True, size=24)
#     city = fields.Char('Ville', size=128)
#     country_code = fields.Char(related='country_id.code', string='Code pays', readonly=True)
#     note_log = fields.Char('Info GEO', size=256)

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
    _description = "Jour RES"

    @api.multi
    @api.depends('equipe_id', 'date', 'is_bloque',
                 'equipe_id.hor_md', 'equipe_id.hor_mf', 'equipe_id.hor_ad', 'equipe_id.hor_af')
    def _compute_is_complet(self):
        if 'tz' not in self._context:
            self = self.with_context(dict(self._context, tz='Europe/Paris'))
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
                    start_flo = start_local.hour + \
                                start_local.minute / 60 + \
                                start_local.second / 3600

                end_local = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(intervention.date_deadline))
                if end_local.day != date_local.day:
                    end_flo = equipe.hor_af
                else:
                    end_flo = start_local.hour + \
                                start_local.minute / 60 + \
                                start_local.second / 3600

                start_end_list.append((start_flo, end_flo))
            start_end_list.sort()

            is_complet = True
            last_end = 0
            for s,e in start_end_list:
                if s - last_end > 0:
                    is_complet = False
                    break
                if e > last_end:
                    last_end = e
            tournee.is_complet = is_complet

    @api.depends('date')
    def _get_jour(self):
        if 'tz' not in self._context:
            self = self.with_context(dict(self._context, tz='Europe/Paris'))
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
    address_id = fields.Many2one('res.partner', string=u'Adresse Référence')
#     commune_id = fields.Many2one('of.commune', 'Code Postal & Ville')
    zip = fields.Char(string='CP', size=24)
    city = fields.Char(string='Ville', size=128)
    country_id = fields.Many2one('res.country', string='Pays')
    distance = fields.Float(string='Eloignement (km)', digits=(12,4), required=True, default=20.0)
    is_complet = fields.Boolean(compute="_compute_is_complet", string='Complet', store=True)
    is_bloque = fields.Boolean(string=u'Bloqué', help=u'Journée bloquée : ne sera pas proposée à la planification')
    is_confirme = fields.Boolean(string=u'Confirmé', default=True, help=u'Une tournée non confirmée sera supprimée si on lui retire ses rendez-vous')

    @api.multi
    def _get_dummy_fields(self):
        if 'tz' not in self._context:
            self = self.with_context(dict(self._context, tz='Europe/Paris'))
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

    @api.onchange('address_id')
    def _onchange_address_id(self):
        if self.address_id:
            address = self.address_id
            self.epi_lat = address.geo_lat
            self.epi_lon = address.geo_lng
#            self.ville = address.commune_id and address.commune_id.id
            self.zip = address.zip
            self.city = address.city

#     @api.onchange('commune_id')
#     def onchange_ville(self):
#         if self.address_id:
#             return
#         if self.commune_id:
#             commune = commune_obj.read(cr, uid, ville, ['zip','city','geo_lat','geo_lng'])
#             self.epi_lat = address.geo_lat
#             self.epi_lon = address.geo_lng
#             self.zip = commune.zip
#             self.city = commune.city
#             data['zip'] = commune['zip']
#             data['city'] = commune['city']
#             data['epi_lat'] = commune['geo_lat']
#             data['epi_lon'] = commune['geo_lng']
#         else:
#             data = {
#                 'zip' : '',
#                 'city': '',
#             }
#         return {'value':data}

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
        mod_obj = self.env['ir.model.data']
        view_id = mod_obj.get_object_reference('of_planning_tournee', 'view_tournee_planification_wizard')[1]

#        self = self.with_context(dict(self._context, active_ids=self._ids))
        planif = self.env['of.tournee.planification'].create({'tournee_id': self.id})

        return {
            'name': 'Planification RDV',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [view_id],
            'res_model': 'of.res.planification',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': planif.id,
        }


# class of_planning_controle(osv.TransientModel):
#     _name = 'of.planning.controle'
#     _description = u'Contrôle des tournées'
# 
#     _columns = {
#         'date_controle': fields.date(u'Le mois à contrôler', required=True),
#         'client_id': fields.one2many('of.planning.controle.client', 'controle_id', 'Client'),
#         'note': fields.text('Note'),
#         'total_planifie': fields.integer(u'RDV planifiés'),
#         'total_a_planifier': fields.integer(u'RDV à planifier'),
#         'total_hors': fields.integer(u'RDV hors tournée'),
#         'total_no_gps': fields.integer(u'RDV sans GPS'),
#     }
# 
#     _rec_name = 'client_id'
# 
#     _defaults = {
#         'date_controle': datetime.now().strftime('%Y-%m-%d'),
#     }
# 
#     def _verif_tournee(self, cr, uid, tournee_tache_gps_dict, tache_id, adr_geo_lat, adr_geo_lng, intervention_date):
#         intervention_in_tournee = False
#         tache_date = False
#         for t_tache_ids, t_epi_lat, t_epi_lon, t_distance, t_date in tournee_tache_gps_dict.itervalues():
#             if intervention_date and t_date != intervention_date:
#                 continue
#             if tache_id in t_tache_ids:
#                 if distance_points(t_epi_lat,t_epi_lon,adr_geo_lat,adr_geo_lng) <= t_distance:
#                     intervention_in_tournee = True
#                     tache_date = t_date
#                     break
#         return {'intervention_in_tournee': intervention_in_tournee, 'tache_date': tache_date}
# 
#     def button_controle(self, cr, uid, ids, context={}, *args):
#         service_obj = self.pool['of.service']
#         intervention_obj = self.pool['of.planning.intervention']
#         res_obj = self.pool['of.planning.res']
#         ids = isinstance(ids, int or long) and [ids] or ids
# 
#         for controle in self.browse(cr, uid, ids):
#             date_controle = datetime.strptime(controle.date_controle, "%Y-%m-%d")
#             mois_id = date_controle.month
#             mois_fin = date(date_controle.year, mois_id, calendar.mdays[mois_id])
#             mois_fin_str = mois_fin.strftime('%Y-%m-%d')
# 
#             mois_debut = date(date_controle.year, mois_id, 1)
#             mois_debut_str = mois_debut.strftime('%Y-%m-%d')
# 
#             # Services pourvus durant le mois
#             cr.execute("SELECT s.id, p.id\n"
#                        "FROM of_planning_intervention AS p\n"
#                        "INNER JOIN of_service AS s\n"
#                        "  ON s.partner_id = p.part_id AND p.tache = s.tache_id\n"
#                        "WHERE p.date >= '%s'\n"
#                        "  AND p.date <= '%s'\n"
#                        "  AND s.state = 'progress'\n"
#                        "  AND p.state NOT IN ('Reporte', 'Inacheve', 'Annule')" % (mois_debut_str, mois_fin_str))
#             plannings_dict = dict(cr.fetchall())
# 
#             # Recherche de tous les services à afficher, avec les droits de l'utilisateur
#             service_ids = service_obj.search(cr, uid, [('state','=','progress'), '|', ('date_next','<=',mois_fin_str), ('id','in',plannings_dict.keys())], order='partner_id', context=context)
# 
#             # Mise en cache du browse_record_list des interventions à parcourir, pour éviter de multiplier les read()
#             intervention_obj.browse(cr, uid, plannings_dict.values(), context=context)
# 
#             # Détection des tournées planifiées dans le mois
#             res_ids = res_obj.search(cr, uid, [('date', '>=', mois_debut_str), ('date','<=',mois_fin_str)], context=context)
#             res_dict = {(res.equipe_id, res.date): res for res in res_obj.browse(cr, uid, res_ids, context=context)}
# 
#             lines = [(5, 0)]
#             total_planifie = 0
#             total_a_planifier = 0
#             total_hors = 0
#             total_no_gps = 0
#             for service in service_obj.browse(cr, uid, service_ids, context=context):
#                 intervention_id = plannings_dict.get(service.id)
#                 res = False
# 
#                 if intervention_id:
#                     # Le service a été pourvu
#                     intervention = intervention_obj.browse(cr, uid, intervention_id, context=context)
#                     date_intervention = intervention.date[:10]
#                     mois_intervention = int(intervention.date[5:7])
#                     res = res_dict.get((intervention.equipe_id, date_intervention), False)
#                     if res:
#                         state = 'correct'
#                         total_planifie += 1
#                     else:
#                         state = 'sans_tournee'
#                         total_hors += 1
#                 else:
#                     # Le service n'a pas été pourvu
#                     date_intervention = False
#                     mois_intervention = max(service.mois_ids, key=lambda x: (x.id <= mois_id, x.id)).id
#                     if service.partner_geo_lat or service.partner_geo_lng:
#                         state = 'attend'
#                         total_a_planifier += 1
#                     else:
#                         state = 'sans_gps'
#                         total_no_gps += 1
#                 lines.append((0, 0, {
#                     'service_id': service.id,
#                     'mois_id': mois_intervention,
#                     'date_intervention': date_intervention,
#                     'res_id': res and res.id,
#                     'state': state,
#                 }))
# 
#             note = total_no_gps and "Veuillez corriger l'adresse du client pour les lignes en gris" or ''
#             controle.write({
#                 'client_id'        : lines,
#                 'total_planifie'   : total_planifie,
#                 'total_a_planifier': total_a_planifier,
#                 'total_hors'       : total_hors,
#                 'total_no_gps'     : total_no_gps,
#                 'note'             : note
#             })
#         return True
# of_planning_controle()
# 
# 
# class of_planning_controle_client(osv.TransientModel):
#     _name = 'of.planning.controle.client'
#     _description = 'Client'
# 
#     _columns = {
#         'controle_id': fields.many2one('of.planning.controle', u'Contrôle des tournées'),
#         'service_id': fields.many2one('of.service', 'Service'),
#         'res_id': fields.many2one('of.planning.res', u'Tournée'),
#         'partner_id': fields.related('service_id', 'partner_id', type="many2one", relation='res.partner', string='Client', oldname='res_partner_id'),
#         'partner_adr_id': fields.related('service_id', 'partner_address_id', type="many2one", relation='res.partner.address', string='Adresse'),
#         'tache_id': fields.related('service_id', 'tache_id', type="many2one", relation='of.planning.tache', string='Tache'),
#         'city': fields.related('partner_adr_id', 'city', type='char', string='Ville'),
#         'mois_ids_dis': fields.related('service_id','mois_ids_dis', type='char', string="Mois"),
#         'mois_id': fields.many2one('of.mois', 'Mois'),
#         'mois_abr': fields.related('mois_id', 'abr', type='char', string='Mois'),
#         'date_intervention': fields.date('Date'),
#         'date_tournee': fields.related('res_id', 'date', type="date", string='Date tournée'),
#         'date_next': fields.related('service_id', 'date_next', type="date", string=u'Prochaine planification'),
#         'state': fields.selection([('sans_gps', 'sans_gps'), ('sans_tournee', 'sans_tournee'), ('correct', 'correct'), ('attend', 'attend')])
#     }
# of_planning_controle_client()
