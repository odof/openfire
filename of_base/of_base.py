# -*- coding: utf-8 -*-

import openerp
from openerp import models, api,tools
from openerp.osv import osv

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

    # Pour afficher dans le menu déroulant de choix de partenaire l'adresse du contact et pas que le nom 
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if context.get('show_address'):
            context = dict(context or {}, of_show_address_line=True)
        return super(ResPartner,self).name_search(cr, uid, name, args, operator, context, limit)
    
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

    def _add_missing_default_values(self, cr, uid, values, context=None):
        # La reference par defaut est celle du parent
        parent_id = values.get('parent_id')
        if parent_id and isinstance(parent_id, (int,long)) and not values.get('ref') and 'default_ref' not in context:
            values['ref'] = self.read(cr, uid, parent_id, ['ref'], context=context)['ref']
        return super(ResPartner,self)._add_missing_default_values(cr, uid, values, context=context)

    def onchange_parent_id(self, cr, uid, ids, parent_id, context=None):
        result = super(ResPartner, self).onchange_parent_id(cr, uid, ids, parent_id, context=context)
        if parent_id:
            result.setdefault('value', {})['ref'] = self.browse(cr, uid, parent_id, context=context).ref
        return result

    @api.model
    def _check_no_ref_duplicate(self, ref):
        if not ref:
            return True
        parent_id = False
        cr = self._cr
        cr.execute("SELECT id,parent_id FROM res_partner WHERE ref = '%s'" % ref)
        while True:
            vals = cr.fetchall()
            ids = []
            for id,pid in vals:
                if pid:
                    if pid not in ids:
                        ids.append(pid)
                elif parent_id:
                    if id != parent_id:
                        raise osv.except_osv(('Erreur'), u"Le n° de compte client est déjà utilisé et doit être unique. (%s)" % (ref,))
                else:
                    parent_id = id
            if not ids:
                break
            cr.execute("SELECT id,parent_id FROM res_partner WHERE id IN %s", (tuple(ids),))
        return True

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        self._check_no_ref_duplicate(vals.get('ref'))
        return res

    @api.model
    def _update_refs(self, new_ref, partner_refs):
        # Avant de mettre a jour les enfants, on verifie que les partenaires avec cette reference ont bien tous un parent commun
        self._check_no_ref_duplicate(new_ref)
        
        to_update_ids = []
        while partner_refs:
            partner, old_ref = partner_refs.pop()
            for child in partner.child_ids:
                if child.ref == old_ref:
                    # La reference du contact etait la meme que celle du parent, on met a jour et on continue le parcours
                    to_update_ids.append(child.id)
                    partner_refs.append((child,old_ref))
        if to_update_ids:
            self.env['res.partner'].browse(to_update_ids).write({'ref':new_ref})
        return True

    @api.multi
    def write(self, vals):
        # Modification de la fonction write pour propager la modification de la reference aux enfants si besoin
        write_ref = 'ref' in vals
        if write_ref:
            # La reference est modifiee, il va falloir propager la nouvelle valeur aux enfants
            ref = vals['ref']
            partner_refs = [(partner,partner.ref) for partner in self if partner.ref != ref]
        super(ResPartner,self).write(vals)
        if write_ref:
            self._update_refs(ref, partner_refs)
        return True
    
    
