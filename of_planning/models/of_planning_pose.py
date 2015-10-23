# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
import time
from datetime import datetime, timedelta

class of_planning_tache(osv.Model):
    _name = "of.planning.tache"
    _description = "Planning OpenFire : Tâches"
    _columns = {
        'name'       : fields.char('Libellé', size=64, required=True),
        'description': fields.text('Description'),
        'verr'       : fields.boolean(u'Verrouillé'),
        'product_id' : fields.many2one('product.product', 'Produit'),
        'active'     : fields.boolean('Actif', required=True),
        'imp_detail' : fields.boolean(u'Imprimer Détail', help=u"""Impression du détail des tâches dans le planning semaine
Si cette option n'est pas cochée, seule la tâche le plus souvent effectuée dans la journée apparaîtra"""),
        'duree'      : fields.float(u'Durée par défaut', digits=(12, 5)),
        'category_id': fields.many2one('hr.employee.category', u"Catégorie d'employés"),
        'is_crm'     : fields.boolean('Tache CRM'),
        'equipe_ids' : fields.many2many('of.planning.equipe', 'equipe_tache_rel', 'tache_id', 'equipe_id', 'Equipes'),
    }

    _defaults = {
        'active' : True,
        'imp_detail': True,
        'is_crm': False,
    }

    def unlink(self, cr, uid, ids, context={}):
        if self.search(cr, uid, [('id','in',ids),('verr','=',True)]):
            raise osv.except_osv('Erreur', 'Vous essayez de supprimer une tâche verrouillée.')
        return super(of_planning_tache, self).unlink(cr, uid, ids, context)

class of_planning_equipe(osv.Model):
    _name = "of.planning.equipe"
    _description = "Equipe de pose"

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'pose_ids': [],
        })
        return super(of_planning_equipe, self).copy(cr, uid, id, default, context=context)

#     def _calcul_cout(self, cr, uid, ids, name, arg, context=None):
#         res = {}
#         for equipe in self.browse(cr, uid, ids):
#             h = a = 0
#             for employee in equipe.employee_ids:
#                 h += employee.cout_horaire
#                 a += employee.cout_annuel
#             res[equipe.id] = {
#                 'cout_horaire': h,
#                 'cout_annuel' : a,
#             }
#         return res

    def _get_employee_equipes(self, cr, uid, ids, context=None):
        result = []
        for emp in self.read(cr, uid, ids, ['equipe_ids']):
            result += emp['equipe_ids']
        return list(set(result))

    _columns = {
        'name'        : fields.char('Equipe', size=128, required=True),
        'note'        : fields.text('Description'),
#         'cout_horaire': fields.function(_calcul_cout, multi='cout',
#                                         store={'of.planning.equipe'  : (lambda self, cr, uid, ids, *a:ids, ['employee_ids'], 10),
#                                               'hr.employee'         : (_get_employee_equipes, ['couts_ids', 'heures', 'jours'], 10)},
#                                         method=True, type='float', string='Cout horaire'),
#         'cout_annuel' : fields.function(_calcul_cout, multi='cout',
#                                         store={'of.planning.equipe'  : (lambda self, cr, uid, ids, *a:ids, ['employee_ids'], 10),
#                                                'hr.employee'         : (_get_employee_equipes, ['couts_ids', 'heures', 'jours'], 10)},
#                                         method=True, type='float', string='Cout annuel'),
        'employee_ids': fields.many2many('hr.employee', 'of_planning_employee_rel', 'employee_id', 'equipe_id', 'Employes'),
        'active'      : fields.boolean('Active'),
#         'color_id'    : fields.many2one('of.calendar.color','Couleur'),
        'category_ids': fields.many2many('hr.employee.category', 'equipe_category_rel', 'equipe_id', 'category_id', 'Categories'),
        'pose_ids'    : fields.one2many('of.planning.pose', 'poseur_id', 'Poses liees'),
        'tache_ids'   : fields.many2many('of.planning.tache', 'equipe_tache_rel', 'equipe_id', 'tache_id', u'Compétences'),
        'hor_md'      : fields.float(u'Matin début', required=True, digits=(12, 5)),
        'hor_mf'      : fields.float('Matin fin', required=True, digits=(12, 5)),
        'hor_ad'      : fields.float(u'Après-midi début', required=True, digits=(12, 5)),
        'hor_af'      : fields.float(u'Après-midi fin', required=True, digits=(12, 5)),
    }

    _defaults = {
        'active': True,
    }
    
    def onchange_employees(self, cr, uid, ids, employee_ids=None):
        emp_obj = self.pool['hr.employee']
        category_ids = []
        if employee_ids and employee_ids[0][0]==6:
            emp_ids = employee_ids[0][2]
            for emp in emp_obj.browse(cr, uid, emp_ids):
                for categ in emp.category_ids:
                    if categ.id not in category_ids:
                        category_ids.append(categ.id)
        return {'value': {'category_ids': category_ids}}
    
    def onchange_horaires(self, cr, uid, ids, hor_md=0, hor_mf=0, hor_ad=0, hor_af=0, context=None):
        if (hor_md != 0) and (hor_mf != 0) and (hor_ad != 0) and (hor_af != 0):
            if (hor_md > 24) or (hor_mf > 24) or (hor_ad > 24) or (hor_af > 24):
                raise osv.except_osv('Attention', u"L'heure doit être inférieure ou égale à 24")
            if(hor_mf < hor_md):
                raise osv.except_osv('Attention', u"L'heure de début ne peut pas être supérieure à l'heure de fin")
            if(hor_af < hor_ad):
                raise osv.except_osv('Attention', u"L'heure de début ne peut pas être supérieure à l'heure de fin")
            if(hor_ad < hor_mf):
                raise osv.except_osv('Attention', u"L'heure de l'après-midi ne peut pas être inférieure à l'heure du matin")
        return None

class of_planning_pose_raison(osv.osv):
    _name = "of.planning.pose.raison"
    _description = "Raisons de pose reportee ou inachevee"

    _columns = {
        'name': fields.char('Libelle', size=128, required=True, select=True),
    }

class of_planning_pose(osv.Model):
    _name = "of.planning.pose"
    _description = "Planning de pose OpenFire"

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
            if pose.tache and pose.tache.category_id:
                res[pose.id] = pose.tache.category_id.id
        return res
    
    def _search_category(self, cr, uid, obj, name, args, context):
        tache_ids = self.pool['of.planning.tache'].search(cr, uid, args, context=context)
        return [('tache', 'in', tache_ids)]

    _columns = {
        'name'                 : fields.char('Libelle', size=64, required=True),
        'date'                 : fields.datetime('Date de pose', required=True),
        'date_from'            : fields.function(lambda *a, **k:{}, method=True, type='date', string=u"Date début"),
        'date_to'              : fields.function(lambda *a, **k:{}, method=True, type='date', string="Date fin"),
        'date_deadline'        : fields.datetime('Deadline'),
        'date_deadline_display': fields.related('date_deadline', type='datetime', string="Date Fin", store=False),
        'duree'                : fields.float('Duree de pose', required=True, digits=(12, 5)),
        'user_id'              : fields.many2one('res.users', 'Utilisateur'),
        'partner_id'           : fields.many2one('res.partner', 'Client'),
        'partner_city'         : fields.function(_get_city, method=True, type='char', string='Ville', readonly=False,
                                                 store={'of.planning.pose'   : (lambda self, cr, uid, ids, *a:ids, ['partner_id'], 10),
                                                        'res.partner'        : (_get_partner_pose_ids, ['address'], 10)}),
        'raison_id'            : fields.many2one('of.planning.pose.raison', 'Raison'),
        'tache'                : fields.many2one('of.planning.tache', 'Tâche', required=True),
        'poseur_id'            : fields.many2one('of.planning.equipe', 'Equipe Pose', required=True),
        'state'                : fields.selection([('Brouillon', 'Brouillon'), ('Planifie', 'Planifié'), ('Confirme', 'Confirmé'), ('Pose', 'Posé'), ('Annule', 'Annulé'), ('Reporte', 'Reporté'), ('Inacheve', 'Inachevé')], 'Etat', size=16, readonly=True),
        'company_id'           : fields.many2one('res.company', 'Magasin'),
        'description'          : fields.text('Description'),
        'hor_md'               : fields.float(u'Matin début', required=True, digits=(12, 5)),
        'hor_mf'               : fields.float('Matin fin', required=True, digits=(12, 5)),
        'hor_ad'               : fields.float(u'Après-midi début', required=True, digits=(12, 5)),
        'hor_af'               : fields.float(u'Après-midi fin', required=True, digits=(12, 5)),
        'hor_sam'              : fields.boolean('Samedi'),
        'hor_dim'              : fields.boolean('Dimanche'),
#         'color'                : fields.function(_get_color, type='char', help=u"Couleur utilisée pour le planning. Dépend de l'équipe de pose et de l'état de la pose"),
#         'sidebar_color'        : fields.related('poseur_id','color_id','color', type='char', help="Couleur pour le menu droit du planning (couleur de base de l'équipe de pose)"),
        'category_id'          : fields.function(_get_category, method=True, type='many2one', obj="hr.employee.category", string=u"Type de tâche", store=False,
                                                 fnct_search=_search_category),
        'verif_dispo'          : fields.boolean(u'Vérif', help=u"Vérifier la disponibilité de l'équipe de pose sur ce créneau", required=True),
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

    def onchange_partner_id(self, cr, uid, ids, partner_id, context={}):
        val = {
            'name': partner_id and self._calc_name(cr, uid, partner_id) or "Pose"
        }
        return {'value':val}

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
        dt_local = fields.datetime.context_timestamp(cr, uid, dt_utc, context=context)

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
    
    def onchange_poseur(self, cr, uid, ids, poseur_id):
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

class res_partner(osv.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    _columns = {
        'pose_ids': fields.one2many('of.planning.pose', 'partner_id', 'Plannings de pose'),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default['pose_ids'] = False
        return super(res_partner, self).copy(cr, uid, id, default, context=context)
