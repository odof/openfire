# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from __future__ import division
from odoo import api, fields, models, _
from datetime import datetime
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import pytz


class OFTrainingModality(models.Model):
    _name = 'of.training.modality'
    _description = u"Modality"

    name = fields.Char(string=u"Name")
    description = fields.Text(string=u"Description")
    sequence = fields.Integer(string=u"Sequence", help=u"Sequence for the handle.", default=10)
    type = fields.Selection([
        ('access', u"Access modality"),
        ('participation', u"Participation modality"),
        ('pedagogic', u"Pedagogic modality"),
        ('technic', u"Technic modality"),
        ('evaluation', u"Evaluation modality"),
        ('contract', u"Contract modality"),
        ], required=True)
    is_printable = fields.Boolean(string=u"Impression", default=False)


class OFTrainingEquipment(models.Model):
    _name = 'of.training.equipment'
    _description = u"Equipment"

    name = fields.Char(string="Name")
    description = fields.Text(string="Description")
    sequence = fields.Integer(string="Sequence", help="Sequence for the handle.", default=10)
    availability = fields.Selection([
        ('limited', 'Limited'),
        ('unlimited', 'Unlimited'),
        ], string="Availability", required=True, default="unlimited")
    type = fields.Selection([
        ('software', 'Software'),
        ('hardware', 'Hardware'),
        ('room', 'Room'),
        ], string="Type")


class OFTrainingProgram(models.Model):
    _name = 'of.training.program'
    _description = u"Program"

    name = fields.Char(string="Name")
    default_code = fields.Char(string="Reference")
    training_objectives = fields.Text(string="Training objectives")
    training_program = fields.Text(string="Detailed program")
    sequence = fields.Integer(string="Sequence", help="Sequence for the handle.", default=10)
    min_participant = fields.Integer(string="Min. participant", default=1)
    max_participant = fields.Integer(string="Max. participant", default=10)
    duration = fields.Float(string="Duration")
    session_id = fields.Many2one(comodel_name="of.training.session", string="Session")
    former_ids = fields.Many2many(
        comodel_name="res.partner", relation="program_former_rel",
        column1="program_id", column2="partner_id", string="Formers")
    modality_ids = fields.Many2many(comodel_name="of.training.modality", string="Modalities")
    product_ids = fields.Many2many(comodel_name="product.template", string="Services")


class OFTrainingSession(models.Model):
    _name = 'of.training.session'
    _description = u"Session"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('valid', 'Valid'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ], string="State", required=True, default="draft")
    name = fields.Char(string="Name")
    sequence = fields.Integer(string="Sequence", help="Sequence for the handle.", default=10)
    line_ids = fields.One2many(
        comodel_name="of.training.session.line", inverse_name="session_id", string="Session Lines")
    equipment_ids = fields.Many2many(comodel_name="of.training.equipment", string="Equipments")


class OFTrainingSessionLine(models.Model):
    _name = 'of.training.session.line'
    _description = u"Session Line"

    name = fields.Char(string="Name")
    sequence = fields.Integer(string="Sequence", help="Sequence for the handle.", default=10)
    nbr_participant = fields.Integer(string="Nbr. of participant", compute="_compute_nbr_participant")
    datetime_start = fields.Datetime(string="Start time", compute="_compute_duration")
    datetime_stop = fields.Datetime(string="End time", compute="_compute_duration")
    duration = fields.Float(string="Duration", compute="_compute_duration")
    session_id = fields.Many2one("of.training.session", string="Session")
    program_id = fields.Many2one("of.training.program", string="Program")
    slot_ids = fields.One2many("of.training.program.slot", "session_line_id", string="Slots")
    participant_line_ids = fields.One2many("of.training.session.participant.line", "session_line_id", string="Participation Lines")
    participant_ids = fields.Many2many("res.partner", "session_line_participant_rel", "session_line_id", "participant_id", string="Participants")

    @api.depends('participant_ids')
    def _compute_nbr_participant(self):
        for session_line in self:
            session_line.nbr_participant = len(session_line.participant_ids)

    @api.depends('slot_ids')
    def _compute_duration(self):
        datetime_start = datetime.max
        datetime_stop = datetime.min
        duration = 0.0
        for line in self:
            for slot in line.slot_ids:
                datetime_start = datetime_start < datetime.strptime(slot.datetime_start, "%Y-%m-%d %H:%M:%S") and datetime_start or datetime.strptime(slot.datetime_start, "%Y-%m-%d %H:%M:%S")
                datetime_stop = datetime_stop > datetime.strptime(slot.datetime_stop, "%Y-%m-%d %H:%M:%S") and datetime_stop or datetime.strptime(slot.datetime_stop, "%Y-%m-%d %H:%M:%S")
                duration = duration + slot.duration

            line.datetime_start = datetime_start
            line.datetime_stop = datetime_stop
            line.duration = duration


class OFTrainingSessionParticipantLine(models.Model):
    _name = 'of.training.session.participant.line'
    _description = u"Participation Line"

    @api.onchange('session_line_id','slot_ids')
    def _onchange_session_line_id(self):
        if self.session_line_id:
            return {'domain': {'slot_ids': [('id', 'in', self.session_line_id.slot_ids.ids)]}}

    @api.model
    def _domain_slot_ids(self):
        session_line_id = self.env['of.training.session.line'].browse(self._context.get('active_id', False))
        if session_line_id:
            return [('id', 'in', session_line_id.slot_ids.ids)]

    name = fields.Char(string="Name", related="partner_id.name")
    sequence = fields.Integer(string="Sequence", help="Sequence for the handle.", default=10)
    partner_id = fields.Many2one("res.partner", string="Participant")
    session_line_id = fields.Many2one("of.training.session.line", string="Session Line")
    program_id = fields.Many2one("of.training.program", string="Program", related="session_line_id.program_id")
    slot_ids = fields.Many2many("of.training.program.slot", "program_slot_session_participant_line_rel", "session_participant_line_id", "slot_id", string="Slots", domain=_domain_slot_ids)
    participation = fields.Selection([
        ('free', 'Free'),
        ('paid', 'Paid'),
        ], string="Participation", required=True, default="free")
    pre_evaluation = fields.Selection([
        ('to_do', 'To do'),
        ('done', 'Done'),
        ('not_done', 'Not done'),
        ], string="Pre evaluation", required=True, default="not_done")
    hot_evaluation = fields.Selection([
        ('to_do', 'To do'),
        ('done', 'Done'),
        ('not_done', 'Not done'),
        ], string="Hot evaluation", required=True, default="not_done")
    cold_evaluation = fields.Selection([
        ('to_do', 'To do'),
        ('done', 'Done'),
        ('not_done', 'Not done'),
        ], string="Cold evaluation", required=True, default="not_done")
    evaluation_of_prior_learning = fields.Selection([
        ('to_do', 'To do'),
        ('done', 'Done'),
        ('not_done', 'Not done'),
        ], string="Evaluation of prior learning", required=True, default="not_done")
    nbr_slot = fields.Integer(string="Nbr. of slot", compute="_compute_slot_hour")
    duration = fields.Float(string="Nbr. of hour", compute="_compute_slot_hour")

    @api.depends('slot_ids')
    def _compute_slot_hour(self):
        nbr_slot = 0
        duration = 0.0
        for line in self:
            for slot in line.slot_ids:
                nbr_slot = nbr_slot + 1
                duration = duration + slot.duration

            line.nbr_slot = nbr_slot
            line.duration = duration


class OFTrainingProgramSlot(models.Model):
    _name = 'of.training.program.slot'
    _description = u"Program Slot"

    name = fields.Char(string=u"Name", compute='_compute_name')
    datetime_start = fields.Datetime(string=u"Start time", required=True)
    datetime_stop = fields.Datetime(string=u"End time", required=True)
    duration = fields.Float(string=u"Duration", compute='_compute_duration')
    session_line_id = fields.Many2one(comodel_name='of.training.session.line', string=u"Session Line")

    @api.depends('datetime_start','datetime_stop')
    def _compute_duration(self):
        for slot in self:
            if slot.datetime_start and slot.datetime_stop:
                datetime_start = datetime.strptime(slot.datetime_start, "%Y-%m-%d %H:%M:%S")
                datetime_stop = datetime.strptime(slot.datetime_stop, "%Y-%m-%d %H:%M:%S")
                delta = datetime_stop - datetime_start
                slot.duration = float((delta.days * 24) + (delta.seconds / 3600))

    @api.depends('datetime_start','datetime_stop')
    def _compute_name(self):
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        for slot in self:
            name = ""
            if slot.datetime_start and slot.datetime_stop:
                datetime_start = datetime.strftime(pytz.utc.localize(datetime.strptime(slot.datetime_start, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),"%d/%m/%Y %H:%M")
                datetime_stop = datetime.strftime(pytz.utc.localize(datetime.strptime(slot.datetime_stop, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),"%H:%M")
                name = datetime_start + " - " + datetime_stop
            slot.name = name

