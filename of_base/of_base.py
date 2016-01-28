# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import openerp
from openerp import models, fields, api,tools,  _
from openerp.osv import expression

# Migration : champs rml_footer2 n'existe plus dans Odoo 8
#class res_company(osv.Model):
#     _name = "res.company"
#     _inherit = "res.company"
# 
#     _columns = {
#         'rml_footer2': fields.char("Pied de page 2e ligne", size=200),
#     }
# 
#     def on_change_header(self, cr, uid, ids, phone, email, fax, website, reg=False, context=None):
#         return {}

# Migration 8 vers 9 : plus email.template
# class email_template(osv.Model):
#     _inherit = 'email.template'
#     _name = "email.template"
# 
#     # Restreint la possibilité d'ajouter/de supprimer une action d'un modèle de courriel aux seuls utilisateurs qui ont les droits de configuration 
#     def create_action(self, cr, uid, ids, context=None):
# #        data_obj = self.pool['ir.model.data']
# #        user_obj = self.pool['res.user']
# #        dummy,group_id = data_obj.get_object_reference(cr, 1, 'base', 'group_user')
# #        group_ids = user_obj.read(cr, uid, uid, ['groups_id'])['groups_id']
#         ir_model_access = self.pool.get('ir.model.access')
#         if not ir_model_access.check_groups(cr, uid, 'base.group_system'):
#             raise osv.except_osv(('Erreur'), "Vous ne pouvez pas effectuer cette action. Assurez-vous d'avoir les droits d'Administration: Configuration" )
#         return super(email_template,self).create_action(cr, SUPERUSER_ID, ids, context=context)
# 
#     def unlink_action(self, cr, uid, ids, context=None):
#         ir_model_access = self.pool.get('ir.model.access')
#         if not ir_model_access.check_groups(cr, uid, 'base.group_system'):
#             raise osv.except_osv(('Erreur'), "Vous ne pouvez pas effectuer cette action. Assurez-vous d'avoir les droits d'Administration: Configuration" )
#         return super(email_template,self).unlink_action(cr, SUPERUSER_ID, ids, context=context)

class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_default_image(self, is_company, colorize=False):
        # Reecriture de la fonction Odoo pour retirer la couleur de fond aleatoire
        # Ainsi, chaque nouveau partenaire a les memes image/image_medium/image_small
        # Ce qui evite de surcharger le filestore
        img_path = openerp.modules.get_module_resource(
            'base', 'static/src/img', 'company_image.png' if is_company else 'avatar.png')
        with open(img_path, 'rb') as f:
            image = f.read()

        # colorize user avatars
        if not is_company:
            # Un rouge orange, cense rappeler la douce chaleur de la flamme
            # Dans l'atre, les soirs d'hiver, quand le vent glacial rugit au dehors
            image = tools.image_colorize(image, False, (250, 150, 0))

        return tools.image_resize_image_big(image.encode('base64'))

    def _search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        # Modification de la fonction search pour que la recherche sur la reference se fasse aussi sur les parents
        new_args = []
        for arg in args:
            if arg[0] != 'ref':
                new_args.append(arg)
                continue
            op = arg[1]
            negative = op in expression.NEGATIVE_TERM_OPERATORS
            if negative:
                op = expression.TERM_OPERATORS_NEGATION[op]

            args_tmp = ['&', ('ref',op,arg[2]), '|', ('parent_id','=',False), ('ref','!=',False)]
            ids = super(ResPartner, self)._search(cr, models.SUPERUSER_ID, args_tmp, offset=offset, limit=limit, order=order,
                                                  context=context, count=count, access_rights_uid=access_rights_uid)

            if not ids:
                new_args.append(expression.TRUE_LEAF if negative else expression.FALSE_LEAF)
            else:
                if negative:
                    new_args.append('not')
                new_args.append(('id','child_of',ids))
        return super(ResPartner,self)._search(cr, user, new_args, offset=offset, limit=limit, order=order,
                                              context=context, count=count, access_rights_uid=access_rights_uid)

    @api.multi
    def write(self, vals):
        # Modification de la fonction write pour propager la modification de la reference aux enfants si besoin
        write_ref = 'ref' in vals
        if write_ref:
            # La reference est modifie, il va falloir propager la nouvelle valeur aux enfants
            ref = vals['ref']
            partners = [(partner,ref,partner.ref) for partner in self if partner.ref != ref]
        super(ResPartner,self).write(vals)
        if write_ref:
            if not ref:
                # La reference est effacee sur le partenaire courant, on recupere la nouvelle valeur qui vient du parent
                partners = [(partner,partner.ref,old_ref) for partner,ref,old_ref in partners if partner.ref != old_ref]
            to_update_ids = []
            while partners:
                partner, ref, old_ref = partners.pop()
                for child in partner.child_ids:
                    if not child.ref:
                        # Le contact n'a pas de reference, on continue le parcours
                        partners.append((child,ref,old_ref))
                    elif child.ref == old_ref:
                        # La reference du contact etait la meme que celle du parent, on efface et on continue le parcours
                        to_update_ids.append(child.id)
                        partners.append((child,ref,old_ref))
                    elif child.ref == ref:
                        # La reference etait deja a jour, on efface et on s'arrete
                        to_update_ids.append(child.id)
            if to_update_ids:
                self.env['res.partner'].browse(to_update_ids).write({'ref':False})
        return True

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        # Modification de la fonction read pour lire la reference du parent recursivement si la reference n'est pas renseignee
        if fields and 'ref' in fields and 'parent_id' not in fields:
            fields = fields + ['parent_id']
        res = super(ResPartner,self).read(fields=fields, load=load)
        if not fields or 'ref' in fields:
            # Si la reference n'est pas definie, on prend celle du parent
            res_dict = {partner['id']:partner for partner in res}

            # {parent a verifier: [enfants affectes]}
            to_search = {}

            for partner in res:
                if partner['ref']:
                    continue
                p = partner
                while p['parent_id']:
                    pid = p['parent_id']
                    if isinstance(pid, (list,tuple)):
                        pid = pid[0]
                    p = res_dict.get(pid)
                    if not p:
                        # Le parent n'est pas inclus dans la lecture, il faut refaire une lecture pour lui
                        to_search.setdefault(pid,[]).append(partner)
                        break
                    if p['ref']:
                        # Application de la reference du parent au partenaire
                        partner['ref'] = p['ref']
                        break

            if to_search:
                # lecture des references des parents non inclus dans la lecture courante
                parents = self.env['res.partner'].browse(to_search.keys()).read(['ref'])
                for parent in parents:
                    ref = parent['ref']
                    if ref:
                        for partner in to_search[parent['id']]:
                            partner['ref'] = ref
        return res
