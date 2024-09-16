# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import html2plaintext

from odoo.addons.phone_validation.tools import phone_validation


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_thread_by_sms(
        self,
        message,
        recipients_data,
        msg_vals=False,
        sms_numbers=None,
        sms_pid_to_number=None,
        resend_existing=False,
        put_in_queue=False,
        **kwargs,
    ):
        """
        Copy of Odoo code to add our own information in kwargs:
        - sender_id: for OVH senders
        - is_commercial: to manage commercial messages
        - date_send: to choose a date

        See `mail.thread._notify_thread_by_sms()` for more information.
        """
        sms_pid_to_number = sms_pid_to_number if sms_pid_to_number is not None else {}
        sms_numbers = sms_numbers if sms_numbers is not None else []
        sms_create_vals = []
        sms_all = self.env['sms.sms'].sudo()

        # pre-compute SMS data
        body = msg_vals['body'] if msg_vals and 'body' in msg_vals else message.body
        sms_base_vals = {
            'body': html2plaintext(body),
            'mail_message_id': message.id,
            'state': 'outgoing',
        }
        # OF : Add `of_send_date`, `of_is_commercial` and `of_sender_id` to sms_base_vals
        if send_date := kwargs.get('of_send_date'):
            sms_base_vals['state'] = 'to_send'
            sms_base_vals['of_date_send'] = send_date

        if 'of_is_commercial' in kwargs:
            sms_base_vals['of_is_commercial'] = kwargs.get('of_is_commercial')

        if sender_id := kwargs.get('of_sender_id'):
            sms_base_vals['of_sender_id'] = sender_id
        # End OF

        # notify from computed recipients_data (followers, specific recipients)
        partners_data = [r for r in recipients_data if r['notif'] == 'sms']
        partner_ids = [r['id'] for r in partners_data]
        if partner_ids:
            for partner in self.env['res.partner'].sudo().browse(partner_ids):
                number = sms_pid_to_number.get(partner.id) or partner.mobile or partner.phone
                sanitize_res = phone_validation.phone_sanitize_numbers_w_record([number], partner)[number]
                number = sanitize_res['sanitized'] or number
                sms_create_vals.append(dict(sms_base_vals, partner_id=partner.id, number=number))

        # notify from additional numbers
        if sms_numbers:
            sanitized = phone_validation.phone_sanitize_numbers_w_record(sms_numbers, self)
            tocreate_numbers = [value['sanitized'] or original for original, value in sanitized.items()]
            existing_partners_numbers = {vals_dict['number'] for vals_dict in sms_create_vals}
            sms_create_vals += [
                dict(
                    sms_base_vals,
                    partner_id=False,
                    number=n,
                    state='outgoing' if n else 'error',
                    failure_type='' if n else 'sms_number_missing',
                )
                for n in tocreate_numbers
                if n not in existing_partners_numbers
            ]

        # create sms and notification
        existing_pids, existing_numbers = [], []
        if sms_create_vals:
            sms_all |= self.env['sms.sms'].sudo().create(sms_create_vals)

            if resend_existing:
                existing = (
                    self.env['mail.notification']
                    .sudo()
                    .search(
                        [
                            '|',
                            ('res_partner_id', 'in', partner_ids),
                            '&',
                            ('res_partner_id', '=', False),
                            ('sms_number', 'in', sms_numbers),
                            ('notification_type', '=', 'sms'),
                            ('mail_message_id', '=', message.id),
                        ]
                    )
                )
                for n in existing:
                    if n.res_partner_id.id in partner_ids and n.mail_message_id == message:
                        existing_pids.append(n.res_partner_id.id)
                    if not n.res_partner_id and n.sms_number in sms_numbers and n.mail_message_id == message:
                        existing_numbers.append(n.sms_number)

            notif_create_values = [
                {
                    'author_id': message.author_id.id,
                    'mail_message_id': message.id,
                    'res_partner_id': sms.partner_id.id,
                    'sms_number': sms.number,
                    'notification_type': 'sms',
                    'sms_id': sms.id,
                    'is_read': True,  # discard Inbox notification
                    'notification_status': 'ready' if sms.state == 'outgoing' else 'exception',
                    'failure_type': '' if sms.state == 'outgoing' else sms.failure_type,
                }
                for sms in sms_all
                if (sms.partner_id and sms.partner_id.id not in existing_pids)
                or (not sms.partner_id and sms.number not in existing_numbers)
            ]
            if notif_create_values:
                self.env['mail.notification'].sudo().create(notif_create_values)

            if existing_pids or existing_numbers:
                for sms in sms_all:
                    notif = next(
                        (
                            n
                            for n in existing
                            if (n.res_partner_id.id in existing_pids and n.res_partner_id.id == sms.partner_id.id)
                            or (
                                not n.res_partner_id and n.sms_number in existing_numbers and n.sms_number == sms.number
                            )
                        ),
                        False,
                    )
                    if notif:
                        notif.write(
                            {
                                'notification_type': 'sms',
                                'notification_status': 'ready',
                                'sms_id': sms.id,
                                'sms_number': sms.number,
                            }
                        )

        if sms_all and not put_in_queue:
            sms_all.filtered(lambda sms: sms.state == 'outgoing').send(auto_commit=False, raise_exception=False)

        return True
