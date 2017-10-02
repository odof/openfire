# -*- encoding: utf-8 -*-

from openerp import api, models, fields


class of_mois(models.Model):
    _name = 'of.mois'
    _description = u"Mois de l'année"
    _order = 'id'

    name = fields.Char('Mois', size=16)
    abr = fields.Char(u'Abréviation', size=16)


class of_jours(models.Model):
    _name = 'of.jours'
    _description = "Jours de la semaine"
    _order = 'id'

    name = fields.Char('Jour', size=16)
    abr = fields.Char(u'Abréviation', size=16)

