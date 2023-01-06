# -*- coding: utf-8 -*-

from odoo import models, api, fields

from dateutil.relativedelta import relativedelta
from datetime import datetime


class OfLogMessage(models.Model):
    _name = 'of.log.message'
    _order = 'create_date DESC'

    name = fields.Char(string="Titre")
    model = fields.Char(string=u"Modèle")
    type = fields.Char(string="Type d'erreur", default="error")
    message = fields.Text(string="message", required=True)
    function = fields.Char(string="Fonction")
    log_level = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
    ], string="Niveau de log", required=True, default='warning')

    @api.model
    def delete_old_logs(self, day_limit=7):
        if day_limit == 0:  # On ne veut pas que les logs soit supprimés
            return
        remove_from = datetime.today() - relativedelta(days=day_limit)
        st = fields.Datetime.to_string(remove_from)
        self.search([('create_date', '<=', st)]).unlink()

    @api.model
    def new_log(self, obj, name, type, message, function, log_level='warning'):
        model = hasattr(obj, "_name") and obj._name or ""
        self.env['of.log.message'].create({
            'name'     : name,
            'model'    : model,
            'type'     : type,
            'message'  : message,
            'function' : function,
            'log_level': log_level,
        })
