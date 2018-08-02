# -*- coding: utf-8 -*-

from openerp import models, fields, api

class OfPopupWizard(models.TransientModel):
    """API fonction permettant d'afficher un message dans une fenêtre au cours de l'exécution d'une fonction""" 
    _name = "of.popup.wizard"

    message = fields.Text(string='Message')

    # Usage : return self.env['of.popup.wizard'].popup_return(message[, titre])
    @api.multi
    def popup_return(self, message, titre="Information"):
        return {
            'type': 'ir.actions.act_window',
            'name': titre,
            'res_model': 'of.popup.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': str({'default_message': message})
        }
