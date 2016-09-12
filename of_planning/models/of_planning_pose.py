# -*- coding: utf-8 -*-

from openerp import api, models, fields
from openerp.osv import fields as fields_old, osv
import time
from datetime import datetime, timedelta

class of_planning_tache(models.Model):
    _name = "of.planning.tache"
    _description = "Planning OpenFire : Tâches"

    name = fields.Char('Libellé', size=64, required=True)
    description = fields.Text('Description')
    verr = fields.Boolean(u'Verrouillé')
    product_id = fields.Many2one('product.product', 'Produit')
    active = fields.Boolean('Actif', default=True)
    imp_detail = fields.Boolean(u'Imprimer Détail', help=u"""Impression du détail des tâches dans le planning semaine
Si cette option n'est pas cochée, seule la tâche le plus souvent effectuée dans la journée apparaîtra""", default=True)
    duree = fields.Float(u'Durée par défaut', digits=(12, 5), default=1.0)
    category_id = fields.Many2one('hr.employee.category', string=u"Catégorie d'employés")
    is_crm = fields.Boolean(u'Tâche CRM')
    equipe_ids = fields.Many2many('of.planning.equipe', 'equipe_tache_rel', 'tache_id', 'equipe_id', 'Equipes')
    
    def unlink(self, cr, uid, ids, context=None):
        if self.search(cr, uid, [('id','in',ids),('verr','=',True)]):
            raise osv.except_osv('Erreur', 'Vous essayez de supprimer une tâche verrouillée.')
        return super(of_planning_tache, self).unlink(cr, uid, ids, context)

class of_planning_equipe(osv.Model):
    _name = "of.planning.equipe"
    _description = "Equipe de pose"
    _order = "sequence, name"

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default['pose_ids'] = []
        return super(of_planning_equipe, self).copy(cr, uid, id, default, context=context)

    def _get_employee_equipes(self, cr, uid, ids, context=None):
        result = []
        for emp in self.read(cr, uid, ids, ['equipe_ids']):
            result += emp['equipe_ids']
        return list(set(result))

    name = fields.Char('Equipe', size=128, required=True)
    note = fields.Text('Description')
    employee_ids = fields.Many2many('hr.employee', 'of_planning_employee_rel', 'equipe_id', 'employee_id', u'Employés')
    active = fields.Boolean('Actif', default=True)
    category_ids = fields.Many2many('hr.employee.category', 'equipe_category_rel', 'equipe_id', 'category_id', u'Catégories')
    pose_ids = fields.One2many('of.planning.pose', 'poseur_id', u'Poses liées')
    tache_ids = fields.Many2many('of.planning.tache', 'equipe_tache_rel', 'equipe_id', 'tache_id', u'Compétences')
    hor_md = fields.Float(u'Matin début', required=True, digits=(12, 5))
    hor_mf = fields.Float('Matin fin', required=True, digits=(12, 5))
    hor_ad = fields.Float(u'Après-midi début', required=True, digits=(12, 5))
    hor_af = fields.Float(u'Après-midi fin', required=True, digits=(12, 5))
    sequence = fields.Integer(u'Séquence', help=u"Ordre d'affichage (plus petit en premier)")
        

    @api.onchange('employee_ids')
    def onchange_employees(self):
        if not self.category_ids:
            category_ids = []
            for employee in self.employee_ids:
                for category in employee.category_ids:
                    if category.id not in category_ids:
                        category_ids.append(category.id)
            if category_ids:
                self.category_ids = category_ids

    @api.onchange('hor_md','hor_mf','hor_ad','hor_af')
    def onchange_horaires(self):
        hors = (self.hor_md, self.hor_mf, self.hor_ad, self.hor_af)
        if all(hors):
            for hor in hors:
                if hor > 24:
                    raise osv.except_osv('Attention', u"L'heure doit être inférieure ou égale à 24")
            if hors[0] > hors[1] or hors[2] > hors[3]:
                raise osv.except_osv('Attention', u"L'heure de début ne peut pas être supérieure à l'heure de fin")
            if(hors[1] > hors[2]):
                raise osv.except_osv('Attention', u"L'heure de l'après-midi ne peut pas être inférieure à l'heure du matin")

class of_planning_pose_raison(models.Model):
    _name = "of.planning.pose.raison"
    _description = "Raisons de pose reportee ou inachevee"

    name = fields.Char(u'Libellé', size=128, required=True, select=True)

class of_planning_pose(osv.Model):
    _name = "of.planning.pose"
    _description = "Planning de pose OpenFire"
    _inherit = "of.readgroup"

    def _get_city(self, cr, uid, ids, *args):#name, arg, context=None):
        partner_obj = self.pool['res.partner']
        tre = {}
        for pose in self.browse(cr, uid, ids):
            partner = pose.partner_id
            if not partner:
                tre[pose.id] = ''
                continue

            address = partner.address_get(adr_pref=['delivery'])['delivery']
            if address and address != partner.id:
                partner = partner_obj.browse(cr, uid, address)
            tre[pose.id] = partner.city
        return tre

#     def _get_color(self, cr, uid, ids, *args):
#         result = {}
#         for pose in self.browse(cr, uid, ids):
#             poseur = pose.poseur_id
#             cal_color = poseur and poseur.color_id
#             result[pose.id] = cal_color and (pose.state in ('Brouillon','Planifie') and cal_color.color2 or cal_color.color) or ''
#         return result

    def _get_partner_pose_ids(self, cr, uid, ids, context=None):
        result = []
        current_date = time.strftime('%Y-%m-%d %H:%M:00')
        partners = self.browse(cr, uid, ids)
        while partners:
            partner = partners.pop()
            for pose in partner.pose_ids:
                if current_date < pose.date:
                    result.append(pose.id)
            if partner.child_ids:
                partners += partner.child_ids
        return result

    def _get_type_category(self, cr, uid, ids, *args):
        cr.execute('select equipe_id from equipe_category_rel where category_id in %s', (tuple(ids),))
        equipe_ids = map(lambda x: x[0], cr.fetchall())
        pose_ids = []
        for e in self.pool.get('of.planning.equipe').browse(cr, uid, equipe_ids):
            if e.pose_ids:
                for p in e.pose_ids:
                    if p.id not in pose_ids:
                        pose_ids.append(p.id)
        return pose_ids

    def _get_type_equipe(self, cr, uid, ids, *args):
        pose_ids = []
        for e in self.pool.get('of.planning.equipe').browse(cr, uid, ids):
            if e.pose_ids:
                for p in e.pose_ids:
                    if p.id not in pose_ids:
                        pose_ids.append(p.id)
        return pose_ids

    def _get_category(self, cr, uid, ids, field, args, context=None):
        res = {}
        for pose in self.browse(cr, uid, ids):
            res[pose.id] = False
            if pose.tache_id and pose.tache_id.category_id:
                res[pose.id] = pose.tache_id.category_id.id
        return res
    
    def _search_category(self, cr, uid, obj, name, args, context):
        tache_ids = self.pool['of.planning.tache'].search(cr, uid, args, context=context)
        return [('tache_id', 'in', tache_ids)]

    def search_gb_employee_id(self, cr, uid, obj, name, args, context):
        return [('employee_ids', 'in', [args[0][2]])]

    _columns = {
        'name'                 : fields_old.char(u'Libellé', size=64, required=True),
        'date'                 : fields_old.datetime('Date intervention', required=True),
        'date_from'            : fields_old.function(lambda *a, **k:{}, method=True, type='date', string=u"Date début"),
        'date_to'              : fields_old.function(lambda *a, **k:{}, method=True, type='date', string="Date fin"),
        'date_deadline'        : fields_old.datetime('Deadline'),
        'date_deadline_display': fields_old.related('date_deadline', type='datetime', string="Date Fin", store=False),
        'duree'                : fields_old.float('Duree intervention', required=True, digits=(12, 5)),
        'user_id'              : fields_old.many2one('res.users', 'Utilisateur'),
        'partner_id'           : fields_old.many2one('res.partner', 'Client'),
        'partner_city'         : fields_old.function(_get_city, method=True, type='char', string='Ville', readonly=False,
                                                     store={'of.planning.pose'   : (lambda self, cr, uid, ids, *a:ids, ['partner_id'], 10),
                                                            'res.partner'        : (_get_partner_pose_ids, ['address'], 10)}),
        'raison_id'            : fields_old.many2one('of.planning.pose.raison', 'Raison'),
        'tache_id'             : fields_old.many2one('of.planning.tache', 'Tâche', required=True),
        'poseur_id'            : fields_old.many2one('of.planning.equipe', 'Intervenant', required=True),
        'employee_ids'         : fields_old.related('poseur_id', 'employee_ids', type='one2many', relation='hr.employee', string='Intervenants', readonly=True),
        'state'                : fields_old.selection([('Brouillon', 'Brouillon'), ('Planifie', u'Planifié'), ('Confirme', u'Confirmé'),
                                                       ('Pose', u'Réalisé'), ('Annule', u'Annulé'), ('Reporte', u'Reporté'), ('Inacheve', u'Inachevé')],
                                                      'Etat', size=16, readonly=True),
        'company_id'           : fields_old.many2one('res.company', 'Magasin'),
        'description'          : fields_old.text('Description'),
        'hor_md'               : fields_old.float(u'Matin début', required=True, digits=(12, 5)),
        'hor_mf'               : fields_old.float('Matin fin', required=True, digits=(12, 5)),
        'hor_ad'               : fields_old.float(u'Après-midi début', required=True, digits=(12, 5)),
        'hor_af'               : fields_old.float(u'Après-midi fin', required=True, digits=(12, 5)),
        'hor_sam'              : fields_old.boolean('Samedi'),
        'hor_dim'              : fields_old.boolean('Dimanche'),
#         'color'                : fields_old.function(_get_color, type='char', help=u"Couleur utilisée pour le planning. Dépend de l'équipe de pose et de l'état de la pose"),
#         'sidebar_color'        : fields_old.related('poseur_id','color_id','color', type='char', help="Couleur pour le menu droit du planning (couleur de base de l'équipe de pose)"),
        'category_id'          : fields_old.function(_get_category, method=True, type='many2one', obj="hr.employee.category", string=u"Type de tâche", store=False,
                                                 fnct_search=_search_category),
        'verif_dispo'          : fields_old.boolean(u'Vérif', help=u"Vérifier la disponibilité de l'équipe sur ce créneau"),
        'gb_employee_id'       : fields_old.function(lambda *args: [], fnct_search=search_gb_employee_id,
                                                     string="Intervenant", type="many2one", relation="hr.employee", of_custom_groupby=True),
    }
    _defaults = {
        'user_id'    : lambda self, cr, uid, context: uid,
        'company_id' : lambda self, cr, uid, context: self.pool['res.users'].browse(cr, uid, uid).company_id.id,
        'state'      : 'Brouillon',
        'verif_dispo': True,
    }
    _order = 'date'

    def _calc_name(self, cr, uid, partner_id):
        partner_obj = self.pool['res.partner']
        address_id = partner_obj.address_get(cr, uid, [partner_id], ['delivery'])['delivery'] or partner_id
        name = [partner_obj.name_get(cr, uid, [partner_id])[0][1]]
        address = partner_obj.read(cr, uid, address_id, ['zip','city'])
        for field in ('zip','city'):
            if address[field]:
                name.append(address[field])
        return " ".join(name)

    def onchange_partner_id(self, cr, uid, ids, partner_id, tache_id, description, context={}):
        val = {
            'name': partner_id and self._calc_name(cr, uid, partner_id) or "Pose"
        }
        return {'value':val}

    def onchange_tache_id(self, cr, uid, ids, tache_id, partner_id, description):
        val = {}
        if tache_id:
            tache = self.pool['of.planning.tache'].browse(cr, uid, tache_id)
            if tache.duree:
                val['duree'] = tache.duree
        return {'value': val}

    def onchange_date(self, cr, uid, ids, date, duree, hor_md, hor_mf, hor_ad, hor_af, hor_sam, hor_dim, context=None):
        if (hor_md > 24) or (hor_mf > 24) or (hor_ad > 24) or (hor_af > 24):
            raise osv.except_osv('Attention', u"L'heure doit être inferieure ou égale à 24")
        if(hor_mf < hor_md):
            raise osv.except_osv('Attention', u"L'heure de début ne peut pas être supérieure à l'heure de fin")
        if(hor_af < hor_ad):
            raise osv.except_osv('Attention', u"L'heure de début ne peut pas être supérieure à l'heure de fin")
        if(hor_ad < hor_mf):
            raise osv.except_osv('Attention', u"L'heure de l'après-midi ne peut pas être inférieure à l'heure du matin")
        if context is None:
            context = {}
        value = {}
        if not date:
            return value
        if not duree:
            return value

        # Datetime UTC
        dt_utc = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        # Datetime local
        dt_local = fields_old.datetime.context_timestamp(cr, uid, dt_utc, context=context)

        weekday = dt_local.weekday()
        if weekday == 5 and not hor_sam:
            raise osv.except_osv('Attention', u"L'équipe ne travaille pas le samedi")
        elif weekday == 6 and not hor_dim:
            raise osv.except_osv('Attention', u"L'équipe ne travaille pas le dimanche")

        duree_repos = hor_ad - hor_mf
        duree_matin = hor_mf - hor_md
        duree_apres = hor_af - hor_ad
        duree_jour = duree_matin + duree_apres

        dt_heure = dt_local.hour + (dt_local.minute + dt_local.second / 60) / 60
        # Deplacement de l'horaire de debut au debut de la journee pour faciliter le calcul
        if hor_md <= dt_heure <= hor_mf:
            duree += dt_heure - hor_md
        elif hor_ad <= dt_heure <= hor_af:
            duree += duree_matin + dt_heure - hor_ad
        else:
            # L'horaire de debut des travaux est en dehors des heures de travail
            raise osv.except_osv('Attention', u"Il faut respecter l'horaire de travail")
        dt_local -= timedelta(hours=dt_heure)

        if not (hor_sam and hor_dim):
            # Deplacement de l'horaire de debut au debut de la semaine pour faciliter le calcul
            # Le debut de la semaine peut eventuellement etre un dimanche matin
            jours_sem = (weekday + hor_dim) % 6
            dt_local -= timedelta(days=jours_sem)
            duree += jours_sem * duree_jour

            # Ajout des jours de repos a la duree de la tache pour arriver la meme date de fin
            jours = duree // duree_jour
            duree += (hor_sam + hor_dim) * (jours // (7 - hor_sam - hor_dim))

        # Calcul du nombre de jours
        jours, duree = duree // duree_jour, duree % duree_jour

        # Ajout des heures non travaillees de la derniere journee
        duree += hor_md + (duree > duree_matin and duree_repos)

        # Calcul de la nouvelle date
        dt_local += timedelta(days=jours, hours=duree)
        # Conversion en UTC
        dt_utc = dt_local - dt_local.tzinfo._utcoffset
        value['date_deadline'] = value['date_deadline_display'] = dt_utc.strftime("%Y-%m-%d %H:%M:%S")
        return {'value': value}
    
    def onchange_poseur_id(self, cr, uid, ids, poseur_id):
        equipe_obj = self.pool['of.planning.equipe']
        equipe = equipe_obj.browse(cr, uid, poseur_id)
        if equipe.hor_md and equipe.hor_mf and equipe.hor_ad and equipe.hor_af:
            return {'value': {'hor_md': equipe.hor_md, 'hor_mf': equipe.hor_mf, 'hor_ad': equipe.hor_ad, 'hor_af': equipe.hor_af}}
        
    def button_planifier(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'Planifie'})

    def button_confirmer(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'Confirme'})

    def button_poser(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'Pose'})

    def button_reporter(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'Reporte'})

    def button_inachever(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'Inacheve'})

    def button_annuler(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'Annule'})

    def button_brouillon(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'Brouillon'})

    def change_state_after(self, cr, uid, ids, context=None):
        for pose in self.browse(cr, uid, ids):
            state = pose.state
            if state == 'Brouillon': new_state = 'Planifie'
            elif state == 'Planifie': new_state = 'Confirme'
            elif state == 'Confirme': new_state = 'Pose'
            elif state == 'Pose': new_state = 'Annule'
            elif state == 'Annule': new_state = 'Reporte'
            elif state == 'Reporte': new_state = 'Inacheve'
            elif state == 'Inacheve': new_state = 'Brouillon'
        return self.write(cr, uid, ids, {'state': new_state})

    def change_state_before(self, cr, uid, ids, context=None):
        for pose in self.browse(cr, uid, ids):
            state = pose.state
            if state == 'Brouillon': new_state = 'Inacheve'
            elif state == 'Planifie': new_state = 'Brouillon'
            elif state == 'Confirme': new_state = 'Planifie'
            elif state == 'Pose': new_state = 'Confirme'
            elif state == 'Annule': new_state = 'Pose'
            elif state == 'Reporte': new_state = 'Annule'
            elif state == 'Inacheve': new_state = 'Reporte'
        return self.write(cr, uid, ids, {'state': new_state})

    def create(self, cr, user, vals, context=None):
        if vals.get('verif_dispo') and vals.get('date') and vals.get('date_deadline'):
            rdv = self.search(cr, user, [('poseur_id','=',vals.get('poseur_id')),('date','<',vals['date_deadline']),('date_deadline','>',vals['date']), ('state', 'not in', ('Annule','Reporte'))])
            if rdv:
                raise osv.except_osv('Attention', u'Cette équipe a déjà %s rendez-vous sur ce créneau' % (len(rdv),))
        return super(of_planning_pose, self).create(cr, user, vals, context=context)

    def write(self, cr, uid, ids, vals, context={}):
        if context is None: context = {}
        poses = self.read(cr, uid, isinstance(ids, (int, long)) and [ids] or ids, ['poseur_id','date','date_deadline','verif_dispo'])
        for pose in poses:
            if vals.get('verif_dispo',pose['verif_dispo']):
                pose['poseur_id'] = pose['poseur_id'][0]
                pose = {key: vals.get(key,val) for key,val in pose.iteritems()}
                if pose['date'] and pose['date_deadline']:
                    rdv = self.search(cr, uid, [('poseur_id','=',pose['poseur_id']),('date','<',pose['date_deadline']),('date_deadline','>',pose['date']),('id','!=',pose['id']), ('state', 'not in', ('Annule','Reporte'))])
                    if rdv:
                        raise osv.except_osv('Attention', u'Cette équipe a déjà %s rendez-vous sur ce créneau' % (len(rdv),))
        return super(of_planning_pose, self).write(cr, uid, ids, vals, context=context)

    @api.model
    def _read_group_process_groupby(self, gb, query):
        if gb != 'gb_employee_id':
            return super(of_planning_pose, self)._read_group_process_groupby(gb, query)

        alias, _ = query.add_join(
            (self._table, 'of_planning_employee_rel', 'poseur_id', 'equipe_id', 'poseur_id'),
            implicit=False, outer=True,
        )

        return {
            'field': gb,
            'groupby': gb,
            'type': 'many2one',
            'display_format': None,
            'interval': None,
            'tz_convert': False,
            'qualified_field': '"%s".employee_id' % (alias,)
        }

class res_partner(models.Model):
    _inherit = "res.partner"

    pose_ids = fields.One2many('of.planning.pose', 'partner_id', 'Plannings de pose')

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default['pose_ids'] = False
        return super(res_partner, self).copy(cr, uid, id, default, context=context)
