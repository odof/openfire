# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import ValidationError


class OfCommunication(models.Model):
    """
    Class Model qui permet de créer un message(note de patch, alerte de maintenance, etc.)
    """

    _name = 'of.communication'
    _inherit = 'mail.thread'
    _description = 'Message created'
    _order = 'date desc'

    name = fields.Text(string="Title", required=True, help="Title of message")
    date = fields.Date(default=fields.Date.today, required=True, copy=False, help="Post publication date")
    message_type = fields.Selection(
        string="Type",
        selection=[
            ('informative_message', "Informative Message"),
            ('patch_note', "Patch Note"),
            ('non-critical_alert_message', "Non-Critical Alert Message"),
            ('critical_alert_message', "Critical Alert Message"),
        ],
        required=True,
        tracking=True,
        help="Type of message."
        "Depending on its type the notification will have a color which will define its urgency : \n"
        "  * Informative Message in blue \n"
        "  * Patch Note in blue \n"
        "  * Non-Critical Alert Message in orange \n"
        "  * Critical Alert Message in red ",
    )
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('published', "Published"),
            ('edit', "Edit"),
            ('canceled', "Canceled"),
        ],
        required=True,
        default="draft",
        tracking=True,
        help="State of message",
    )
    active = fields.Boolean(string="Archived", default=True)
    start_scheduled_publication = fields.Datetime(
        string="Start of Scheduled Publication",
        readonly=False,
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        help="The message's display date and time.",
    )
    end_scheduled_publication = fields.Datetime(
        string="End of Scheduled Publication",
        readonly=False,
        tracking=True,
        compute='_compute_end_scheduled_publication',
        store=True,
        help="The message's removed date and time. If not set, it stays visible until replaced by a new message.",
    )
    summary = fields.Text(
        required=True,
        tracking=True,
        help="Content of the message notification. The maximum number of characters is 280",
    )
    message = fields.Html(help="Content of the message")
    edited = fields.Boolean(string="Edited", default=False)
    message_style = fields.Selection(
        selection=[
            ('banner', "Banner"),
            ('pop-up', "Pop-up"),
        ],
        compute='_compute_style_of_message',
        readonly=False,
        store=True,
        help="Style of message. \n"
        "Depending on its style, the notification will have a different form : \n"
        "  * Banner : a banner will appear at the top of the customer page \n"
        "  * Pop-up : a pop-up will appear at the top right of the customer page \n",
    )

    def action_button_publish(self):
        """
        Fonction qui permet de publier le message que si son état est : 'brouillon'
        """
        for record in self:
            if record.state in ['published', 'edit', 'canceled']:
                raise exceptions.UserError(_("You can only publish message in 'Draft' state."))
            record.state = 'published'

    def action_all_publish(self):
        """
        Fonction qui permet de publier tout les messages dont l'état est : 'brouillon'
        """
        for record in self:
            if record.state in ['draft', 'edit']:
                record.state = 'published'

    def action_button_edit(self):
        """
        Fonction qui permet d'éditer un message dont l'état est : 'publier'
        """
        for record in self:
            if record.state not in ['published']:
                raise exceptions.UserError(_("You can only edit message in 'Published' state."))
            record.state = 'edit'
            record.edited = True

    def action_button_publish_edit(self):
        """
        Fonction qui permet de publier un message dont l'état est : 'éditer'
        """
        for record in self:
            if record.state in ['published', 'canceled']:
                raise exceptions.UserError(_("You can only publish message in 'Edit' state."))
            record.state = 'published'

    def action_button_cancel(self):
        """
        Fonction qui permet d'annuler un message dont l'état est : 'brouillon'
        """
        for record in self:
            if record.state in ['published']:
                raise exceptions.UserError(_("You can only cancel message in \'Draft\' state."))
            record.state = 'canceled'

    def unlink(self):
        """
        Fonction qui permet de supprimer un message dont l'état est : 'annuler'
        """
        for record in self:
            if not self.env.context.get('of_force_message_delete') and record.state != 'canceled':
                raise exceptions.UserError(_("You can only delete messages that are in 'Canceled' state."))
        return super().unlink()

    @api.depends('message_type')
    def _compute_style_of_message(self):
        """
        Fonction qui calcule si le message est une alerte non-critique/critique et lui donne un style
        """
        for message_type in self:
            if message_type.message_type in ['non-critical_alert_message', 'critical_alert_message']:
                message_type.message_style = 'banner'
            else:
                message_type.message_style = 'pop-up'

    @api.depends('start_scheduled_publication')
    def _compute_end_scheduled_publication(self):
        """
        Fonction qui calcule une fin de publication d'un message
        en fonction du paramètre donner dans la configuration de odoo (10 jour de base)
        """
        cfg = self.env['ir.config_parameter'].sudo()
        delay = int(cfg.get_param('of_communication.delay_end_scheduled', 10))
        for message_end_scheduled in self:
            message_end_scheduled.end_scheduled_publication = (
                message_end_scheduled.start_scheduled_publication + timedelta(days=delay)
            )

    @api.constrains('summary')
    def _check_char_max_summary(self):
        """
        Fonction qui permet de ne pas dépasser 280 caractère dans le résumé
        """
        for record in self:
            if len(record.summary) > 280:
                raise ValidationError(_("You cannot have more than 280 characters in the summary"))
