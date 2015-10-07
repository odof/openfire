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

from openerp.osv import fields, osv
from openerp import SUPERUSER_ID

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
