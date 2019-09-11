# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import OrderedSet

class Stage(models.Model):
    _inherit = "note.stage"

    active = fields.Boolean("Active", default=True)

class Tag(models.Model):
    _inherit = "note.tag"

    active = fields.Boolean("Active", default=True)

class Note(models.Model):
    _inherit = 'note.note'

    def _default_stage_id(self):
        return self.env['note.stage'].search([], limit=1)

    # stage_id devient un champ many2one classique.
    # De ce fait, et par la surcharge de read_group(), stage_ids n'est plus jamais utilisé.
    stage_id = fields.Many2one(
        'note.stage', string='Stage', compute=False, inverse=False, store=True,
        default=lambda self: self._default_stage_id())
    of_user_ids = fields.Many2many('res.users', 'note_users_rel', 'note_id', 'user_id', string='Utilisateurs concernés')
    of_partner_id = fields.Many2one('res.partner', string='Client', ondelete='cascade')

    @api.model_cr_context
    def _auto_init(self):
        """
        À l'installation du module, l'étape de la note est remplie avec l'étape associée pour son propriétaire.
        """
        cr = self._cr
        fill_stage_id = False
        if self._auto:
            cr.execute("SELECT * FROM information_schema.columns WHERE table_name = 'note_note' AND column_name = 'stage_id'")
            fill_stage_id = not bool(cr.fetchall())

        res = super(Note, self)._auto_init()
        if fill_stage_id:
            # Use self.pool as self.env is not yet defined
            cr.execute("UPDATE note_note AS nn "
                       "SET stage_id = rel.stage_id\n"
                       "FROM note_stage_rel AS rel\n"
                       "INNER JOIN note_stage AS ns ON ns.id = rel.stage_id\n"
                       "WHERE rel.note_id = nn.id AND ns.user_id = nn.user_id")
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if groupby and groupby[0] == "stage_id":
            # Copie de la fonction read_group de models.py afin d'annuler la surcharge dans le module note
            result = self._read_group_raw(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

            groupby = [groupby] if isinstance(groupby, basestring) else list(OrderedSet(groupby))
            dt = [
                f for f in groupby
                if self._fields[f.split(':')[0]].type in ('date', 'datetime')
            ]

            # iterate on all results and replace the "full" date/datetime value
            # (range, label) by just the formatted label, in-place
            for group in result:
                for df in dt:
                    # could group on a date(time) field which is empty in some
                    # records, in which case as with m2o the _raw value will be
                    # `False` instead of a (value, label) pair. In that case,
                    # leave the `False` value alone
                    if group.get(df):
                        group[df] = group[df][1]
            return result
        return super(Note, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
