# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "openfire_custom")
class TestSMSComposerSender(TransactionCase):
    def setUp(self):
        super().setUp()

        self.partner_sms = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "mobile": "123456789",
            }
        )

        self.sms_default_sender = self.env["of.sms.sender"].create(
            {
                "name": "Default Sender",
                "by_default": True,
            }
        )
        self.sms_sender_contact = self.env["of.sms.sender"].create(
            {
                "name": "Contact Sender",
                "model": self.env.ref("base.model_res_partner").id,
            }
        )
        self.sms_sender_contact_default = self.env["of.sms.sender"].create(
            {
                "name": "Contact Default Sender",
                "model": self.env.ref("base.model_res_partner").id,
                "by_default": True,
            }
        )

    def _get_composer_values(self):
        values = (
            self.env["sms.composer"]
            .with_context(**{"active_model": "res.partner", "active_id": self.partner_sms.id})
            .default_get([])
        )
        values.update({"body": "Test SMS"})
        return values

    def test_01_sms_composer_model_default_sender(self):
        """
        Test the behavior when there is a default sender for the model.
        """
        composer = self.env["sms.composer"].create(self._get_composer_values())
        self.assertEqual(composer.of_sender_id, self.sms_sender_contact_default)

    def test_02_sms_composer_model_first_sender(self):
        """
        Test the behavior when there is no default sender for the model but there are other senders for this model.
        """
        self.sms_sender_contact_default.by_default = False
        composer = self.env["sms.composer"].create(self._get_composer_values())
        self.assertEqual(composer.of_sender_id, self.sms_sender_contact)

    def test_03_sms_composer_default_sender(self):
        """
        Test the behavior when there are no senders for the model.
        """
        self.env["of.sms.sender"].search([("model", "=", self.env.ref("base.model_res_partner").id)]).unlink()
        composer = self.env["sms.composer"].create(self._get_composer_values())
        self.assertEqual(composer.of_sender_id, self.sms_default_sender)

    def test_04_sms_composer_no_sender(self):
        """
        Test the behavior when there are no senders at all.
        """
        self.env["of.sms.sender"].search([]).unlink()
        with self.assertRaises(UserError) as no_sender_error:
            self.env["sms.composer"].create(self._get_composer_values())
        self.assertEqual(
            "Erreur ! (#ED100)\n\nAucun expéditeur trouvé. Veuillez le configurer.", no_sender_error.exception.args[0]
        )
