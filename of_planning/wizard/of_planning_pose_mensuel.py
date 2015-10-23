# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from datetime import datetime, timedelta, date
from lxml import etree
from dateutil.relativedelta import relativedelta

class of_planning_pose_mensuel(osv.TransientModel):
    _name = 'of.planning.pose.mensuel'
    _description = 'Planning Mensuel'
    
    def get_client_name(self, cr, uid, val_dict, champ):
        res = ''
        if champ in val_dict.keys():
            for val in val_dict[champ]:
                res += val + '\n'
        res.strip('\n')
        return res
    
    def get_debut_fin(self, cr, uid):
        date_today = datetime.now().date()
        date_mois = int(date_today.strftime('%m'))
        date_annee = int(date_today.strftime('%Y'))
        mois_debut = date(date_annee, date_mois, 1)
        mois_debut_jour_name = mois_debut.strftime('%A')
        debut_date = mois_debut
        if mois_debut_jour_name != 'lundi':
            debut_date = mois_debut - timedelta(days=mois_debut.weekday())
        fin_date = debut_date + timedelta(days=40)
        return {'debut': debut_date, 'fin': fin_date, 'mois_debut': mois_debut}
    
    def create_lines(self, cr, uid, debut_date, fin_date, jour_travail='vendredi'):
        planning_pose_obj = self.pool.get('of.planning.pose')
        partner_obj = self.pool.get('res.partner')
        planning_equipe_obj = self.pool.get('of.planning.equipe')

        lines = [(5, 0)]

        
        if jour_travail == 'samedi':
            # tous les poses dans ce mois (6 jours dans la semaine)
            num_jour_dict = {1: 'lun1', 2: 'mar1', 3: 'mer1', 4: 'jeu1', 5: 'ven1', 6: 'sam1',
                             7: 'lun2', 8: 'mar2', 9: 'mer2', 10: 'jeu2', 11: 'ven2', 12: 'sam2',
                             13: 'lun3', 14: 'mar3', 15: 'mer3', 16: 'jeu3', 17: 'ven3', 18: 'sam3',
                             19: 'lun4', 20: 'mar4', 21: 'mer4', 22: 'jeu4', 23: 'ven4', 24: 'sam4',
                             25: 'lun5', 26: 'mar5', 27: 'mer5', 28: 'jeu5', 29: 'ven5', 30: 'sam5',
                             31: 'lun6', 32: 'mar6', 33: 'mer6', 34: 'jeu6', 35: 'ven6', 36: 'sam6'}
        elif jour_travail == 'dimanche':
            # tous les poses dans ce mois (7 jours dans la semaine)
            num_jour_dict = {1: 'lun1', 2: 'mar1', 3: 'mer1', 4: 'jeu1', 5: 'ven1', 6: 'sam1', 7: 'dim1',
                             8: 'lun2', 9: 'mar2', 10: 'mer2', 11: 'jeu2', 12: 'ven2', 13: 'sam2', 14: 'dim2',
                             15: 'lun3', 16: 'mar3', 17: 'mer3', 18: 'jeu3', 19: 'ven3', 20: 'sam3', 21: 'dim3',
                             22: 'lun4', 23: 'mar4', 24: 'mer4', 25: 'jeu4', 26: 'ven4', 27: 'sam4', 28: 'dim4',
                             29: 'lun5', 30: 'mar5', 31: 'mer5', 32: 'jeu5', 33: 'ven5', 34: 'sam5', 35: 'dim5',
                             36: 'lun6', 37: 'mar6', 38: 'mer6', 39: 'jeu6', 40: 'ven6', 41: 'sam6', 42: 'dim6'}
        else:
            # tous les poses dans ce mois (5 jours dans la semaine)
            num_jour_dict = {1: 'lun1', 2: 'mar1', 3: 'mer1', 4: 'jeu1', 5: 'ven1', 
                             6: 'lun2', 7: 'mar2', 8: 'mer2', 9: 'jeu2', 10: 'ven2',
                             11: 'lun3', 12: 'mar3', 13: 'mer3', 14: 'jeu3', 15: 'ven3',
                             16: 'lun4', 17: 'mar4', 18: 'mer4', 19: 'jeu4', 20: 'ven4',
                             21: 'lun5', 22: 'mar5', 23: 'mer5', 24: 'jeu5', 25: 'ven5',
                             26: 'lun6', 27: 'mar6', 28: 'mer6', 29: 'jeu6', 30: 'ven6'}
            
        state_dict = {'Brouillon': 'B', 'Planifie': 'P', 'Confirme': 'C', 'Pose': 'P', 'Reporte': 'R', 'Inacheve': 'I', 'Annule': 'A'}
        
        equipe_client_day_dict = {}
        
        now_date = debut_date
        i = 1
        while now_date <= fin_date:
            now_date_str = now_date.strftime('%Y-%m-%d')
            pose_ids = planning_pose_obj.search(cr, uid, [('state', 'not in', ('Reporte', 'Inacheve', 'Annule')), ('date', '<=', now_date_str), 
                                                          ('date_deadline', '>=', now_date_str)], order='date')
            for pose in planning_pose_obj.browse(cr, uid, pose_ids):
                if pose.partner_id and pose.partner_id.name:
                    partner = pose.partner_id
                    zip_city = ''
                    address_id = pose.partner_id.address_get(adr_pref=['delivery'])['delivery']
                    if address_id and address_id != pose.partner_id.id:
                        partner = partner_obj.browse(cr, uid, address_id)
                    zip_city = "%s %s" % (partner.zip or '', partner.city or '')
                    zip_city = zip_city.strip()[:27]
                    lib = "[%s]%s\n%s" % (state_dict[pose.state], pose.partner_id.name, zip_city)
                    equipe_client_day_dict.setdefault(pose.poseur_id.id, {}).setdefault(num_jour_dict[i], []).append(lib)

            if jour_travail == 'samedi':
                if i % 6 == 0:    # 6 jours par semaine
                    now_date += timedelta(days=2)
                else:
                    now_date += timedelta(days=1)
            elif jour_travail == 'vendredi':
                if i % 5 == 0:    # 5 jours par semaine
                    now_date += timedelta(days=3)
                else:
                    now_date += timedelta(days=1)
            else:
                now_date += timedelta(days=1)
            i += 1
            
        #for equipe in equipe_client_day_dict.keys():
        # tous les equipes actives
        all_equipe_ids = planning_equipe_obj.search(cr, uid, [], order='name')
        for equipe in all_equipe_ids:
            equipe_name = planning_equipe_obj.read(cr, uid, equipe, ['name'])['name']
            values = {'equipe_id': equipe, 'equipe_id2': equipe_name, 'equipe_id3': equipe_name, 'equipe_id4': equipe_name, 'equipe_id5': equipe_name, 
                      'equipe_id6': equipe_name}
            for nj in num_jour_dict.values():
                if equipe in equipe_client_day_dict.keys():
                    values[nj] = self.get_client_name(cr, uid, equipe_client_day_dict[equipe], nj)
                else:
                    values[nj] = self.get_client_name(cr, uid, {}, nj)
            lines.append((0, 0, values))
            
        return lines
    
    def _get_debut(self, cr, uid, context=None):
        res = self.get_debut_fin(cr, uid)
        return res['debut'].strftime('%Y-%m-%d')
    
    def _get_mois_debut(self, cr, uid, context=None):
        res = self.get_debut_fin(cr, uid)
        return res['mois_debut'].strftime('%Y-%m-%d')
    
    def _get_mois(self, cr, uid, context=None):
        date_today = datetime.now().date()
        return date_today.strftime('%Y-%m-%d')
    
    def _get_fin(self, cr, uid, context=None):
        res = self.get_debut_fin(cr, uid)
        return res['fin'].strftime('%Y-%m-%d')
    
    def _get_lines(self, cr, uid, context=None):
        debut_fin = self.get_debut_fin(cr, uid)
        debut_date = debut_fin['debut']
        fin_date = debut_fin['fin']
        lines = self.create_lines(cr, uid, debut_date, fin_date)
        return lines
    
    _columns = {
        'date_debut': fields.date(u'Date D\u00E9but'),
        'date_fin': fields.date('Date Fin'),
        'date_mois_debut': fields.date(u'Permier jour du mois de Date d\u00E9but'),
        'mois': fields.date('Mois du planning'),
        'jour_travail': fields.selection([('vendredi', 'Lundi au Vendredi'), ('samedi', 'Lundi au Samedi'), ('dimanche', 'Lundi au Dimanche')], 'Jours',
                                         required=True),
        'line_ids': fields.one2many('of.planning.pose.mensuel.line', 'mensuel_id', 'Lignes'),
    }
    
    _rec_name = 'date_debut'
    
    _defaults = {
        'line_ids': _get_lines,
        'date_debut': _get_debut,
        'date_fin': _get_fin,
        'date_mois_debut': _get_mois_debut,
        'mois': _get_mois,
        'jour_travail': 'vendredi',
    }
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        res = super(of_planning_pose_mensuel, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        mensuel_id = context.get('active_id', False)
        jour_travail = 'vendredi'
        debut_date = False
        if mensuel_id:
            mensuel = self.browse(cr, uid, mensuel_id)
            jour_travail = mensuel.jour_travail or 'vendredi'
            debut_date = mensuel.date_debut or False
        champ_list = ['lun1', 'mar1', 'mer1', 'jeu1', 'ven1', 'sam1', 'dim1', 'lun2', 'mar2', 'mer2', 'jeu2', 'ven2', 'sam2', 'dim2',
                      'lun3', 'mar3', 'mer3', 'jeu3', 'ven3', 'sam3', 'dim3', 'lun4', 'mar4', 'mer4', 'jeu4', 'ven4', 'sam4', 'dim4',
                      'lun5', 'mar5', 'mer5', 'jeu5', 'ven5', 'sam5', 'dim5', 'lun6', 'mar6', 'mer6', 'jeu6', 'ven6', 'sam6', 'dim6']
        if debut_date:
            debut_date = datetime.strptime(debut_date, '%Y-%m-%d')
        else:
            debut_fin = self.get_debut_fin(cr, uid)
            debut_date = debut_fin['debut']
        for field in res['fields']:
            if field == 'line_ids':
                now_date = debut_date
                doc = etree.XML(res['fields'][field]['views']['tree']['arch'])
                for champ in champ_list:
                    for node in doc.xpath("//field[@name='" + champ + "']"):
                        if (jour_travail == 'vendredi') and (('sam' in champ) or ('dim' in champ)):
                            node.set('invisible', '1')
                            doc.remove(node)
                        elif (jour_travail == 'samedi') and ('dim' in champ):
                            node.set('invisible', '1')
                            doc.remove(node)
                        else:
                            node.set('string', now_date.strftime('%A').capitalize() + ' ' + now_date.strftime('%d/%m/%y'))
                    now_date += timedelta(days=1)
                res['fields'][field]['views']['tree']['arch'] = etree.tostring(doc)
                 
                now_date = debut_date       
                doc_form = etree.XML(res['fields'][field]['views']['form']['arch'])
                for champ in champ_list:
                    for node in doc_form.xpath("//field[@name='" + champ + "']"):
                        if (jour_travail == 'vendredi') and (('sam' in champ) or ('dim' in champ)):
                            node.set('invisible', '1')
                            doc_form.remove(node)
                        elif (jour_travail == 'samedi') and ('dim' in champ):
                            node.set('invisible', '1')
                            doc_form.remove(node)
                        else:
                            node.set('string', now_date.strftime('%A').capitalize() + ' ' + now_date.strftime('%d/%m/%y'))
                    now_date += timedelta(days=1)
                    
                res['fields'][field]['views']['form']['arch'] = etree.tostring(doc_form)
                
        return res
    
    def onchange_mois(self, cr, uid, ids, mois):
        mois_datetime = datetime.strptime(mois, '%Y-%m-%d')
        date_mois = int(mois_datetime.strftime('%m'))
        date_annee = int(mois_datetime.strftime('%Y'))
        date_mois_debut = date(date_annee, date_mois, 1)
        mois_debut_jour_name = date_mois_debut.strftime('%A')
        date_debut = date_mois_debut
        if mois_debut_jour_name != 'lundi':
            date_debut -= timedelta(days=date_debut.weekday())
        date_fin = date_debut + timedelta(days=40)
        date_debut_str = date_debut.strftime('%Y-%m-%d')
        date_fin_str = date_fin.strftime('%Y-%m-%d')
        date_mois_debut_str = date_mois_debut.strftime('%Y-%m-%d')
        return {'value': {'date_debut': date_debut_str, 'date_fin': date_fin_str, 'date_mois_debut': date_mois_debut_str}}
    
    def button_search(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        planning_obj = self.pool.get('of.planning.pose')
        view_obj = mod_obj.get_object_reference(cr, uid, 'of_planning', 'of_planning_mensuel_view_form')
        view_id = view_obj and view_obj[1] or False,
        view_id = list(view_id)
        view_id = view_id[0]
        
        res_id = ids and ids[0] or False
        if res_id:
            planning_men = self.browse(cr, uid, res_id)
            date_debut = datetime.strptime(planning_men.date_debut, '%Y-%m-%d')
            date_fin = date_debut + timedelta(days=40)
            jour_travail = planning_men.jour_travail
            lines = self.create_lines(cr, uid, date_debut, date_fin, jour_travail)
            if len(lines):
                self.write(cr, uid, res_id, {'line_ids': lines})
        
        return {
            'name': 'Planning Mensuel',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [view_id],
            'res_model': 'of.planning.pose.mensuel',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': res_id,
        }
        
    def refresh_planning_mensuel(self, cr, uid, ids, direct, context=None):
        mod_obj = self.pool.get('ir.model.data')
        view_obj = mod_obj.get_object_reference(cr, uid, 'of_planning', 'of_planning_mensuel_view_form')
        view_id = view_obj and view_obj[1] or False,
        view_id = list(view_id)
        view_id = view_id[0]
        
        ids = ids and isinstance(ids, int or long) and [ids] or ids
        if ids:
            pm = self.browse(cr, uid, ids[0])
            date_mois_debut_old = datetime.strptime(pm.date_mois_debut, '%Y-%m-%d')
            if direct == 'before':
                date_mois_debut = date_mois_debut_old - relativedelta(months=1)
            else:
                date_mois_debut = date_mois_debut_old + relativedelta(months=1)
            mois_debut_jour_name = date_mois_debut.strftime('%A')
            debut_date = date_mois_debut
            if mois_debut_jour_name != 'lundi':
                debut_date = date_mois_debut - timedelta(days=date_mois_debut.weekday())
            date_fin = debut_date + timedelta(days=40)
            jour_travail = pm.jour_travail
            lines = self.create_lines(cr, uid, debut_date, date_fin, jour_travail)
            if len(lines):
                self.write(cr, uid, ids[0], {'line_ids': lines})
            debut_date_str = debut_date.strftime('%Y-%m-%d')
            date_fin_str = date_fin.strftime('%Y-%m-%d')
            date_mois_debut_str = date_mois_debut.strftime('%Y-%m-%d')
            pm.write({'date_debut': debut_date_str, 'date_fin': date_fin_str, 'date_mois_debut': date_mois_debut_str, 'mois': date_mois_debut_str})
            return {
                'name': 'Planning Mensuel',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': [view_id],
                'res_model': 'of.planning.pose.mensuel',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': ids and ids[0] or False,
            }
    
    def button_before(self, cr, uid, ids, context=None):
        return self.refresh_planning_mensuel(cr, uid, ids, 'before', context)
    
    def button_next(self, cr, uid, ids, context=None):
        return self.refresh_planning_mensuel(cr, uid, ids, 'after', context)

class of_planning_pose_mensuel_line(osv.TransientModel):
    _name = 'of.planning.pose.mensuel.line'
    _description = 'Lignes de Planning Mensuel'
    
    _rec_name = 'equipe_id'
    
    _columns = {
        'equipe_id': fields.many2one('of.planning.equipe', 'Equipe'),
        'equipe_id2': fields.related('equipe_id', 'name', type='char', string='Equipe'),
        'equipe_id3': fields.related('equipe_id', 'name', type='char', string='Equipe'),
        'equipe_id4': fields.related('equipe_id', 'name', type='char', string='Equipe'),
        'equipe_id5': fields.related('equipe_id', 'name', type='char', string='Equipe'),
        'equipe_id6': fields.related('equipe_id', 'name', type='char', string='Equipe'),
        'mensuel_id': fields.many2one('of.planning.pose.mensuel', 'Mensuel'),
        'lun1': fields.text('Lun1', size=64),
        'mar1': fields.text('Mar1', size=64),
        'mer1': fields.text('Mer1', size=64),
        'jeu1': fields.text('Jeu1', size=64),
        'ven1': fields.text('Ven1', size=64),
        'sam1': fields.text('Sam1', size=64),
        'dim1': fields.text('Dim1', size=64),
        'lun2': fields.text('Lun2', size=64),
        'mar2': fields.text('Mar2', size=64),
        'mer2': fields.text('Mer2', size=64),
        'jeu2': fields.text('Jeu2', size=64),
        'ven2': fields.text('Ven2', size=64),
        'sam2': fields.text('Sam2', size=64),
        'dim2': fields.text('Dim2', size=64),
        'lun3': fields.text('Lun3', size=64),
        'mar3': fields.text('Mar3', size=64),
        'mer3': fields.text('Mer3', size=64),
        'jeu3': fields.text('Jeu3', size=64),
        'ven3': fields.text('Ven3', size=64),
        'sam3': fields.text('Sam3', size=64),
        'dim3': fields.text('Dim3', size=64),
        'lun4': fields.text('Lun4', size=64),
        'mar4': fields.text('Mar4', size=64),
        'mer4': fields.text('Mer4', size=64),
        'jeu4': fields.text('Jeu4', size=64),
        'ven4': fields.text('Ven4', size=64),
        'sam4': fields.text('Sam4', size=64),
        'dim4': fields.text('Dim4', size=64),
        'lun5': fields.text('Lun5', size=64),
        'mar5': fields.text('Mar5', size=64),
        'mer5': fields.text('Mer5', size=64),
        'jeu5': fields.text('Jeu5', size=64),
        'ven5': fields.text('Ven5', size=64),
        'sam5': fields.text('Sam5', size=64),
        'dim5': fields.text('Dim5', size=64),
        'lun6': fields.text('Lun6', size=64),
        'mar6': fields.text('Mar6', size=64),
        'mer6': fields.text('Mer6', size=64),
        'jeu6': fields.text('Jeu6', size=64),
        'ven6': fields.text('Ven6', size=64),
        'sam6': fields.text('Sam6', size=64),
        'dim6': fields.text('Dim6', size=64),
    }
