# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo import Command
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase

from odoo.addons.of_geolocalize.wizards.of_geo_wizard import OFGeoWizard

from .side_effects import (
    side_effects_test_03,
    side_effects_test_04,
    side_effects_test_05,
    side_effects_test_06,
    side_effects_test_07,
)


@tagged("post_install", "-at_install", "openfire_custom")
class TestOfGeoWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create Partners
        cls.partner_01 = cls.env['res.partner'].create(
            {
                'name': 'Partner_01',
                'street': '1 Rue de la Terre Victoria',
                'zip': '35760',
                'city': 'Saint-Grégoire',
                'of_geocoding_state': 'not_tried',
                'of_precision': 'unknown',
            }
        )
        cls.partner_02 = cls.env['res.partner'].create(
            {
                'name': 'Partner_02',
                'zip': '35000',
                'city': 'Rennes',
                'of_geocoding_state': 'not_tried',
                'of_precision': 'unknown',
            }
        )
        cls.partner_03 = cls.env['res.partner'].create(
            {
                'name': 'Partner_03',
                'city': 'Paris',
                'of_geocoding_state': 'success',
                'of_precision': 'low',
            }
        )
        cls.partner_04 = cls.env['res.partner'].create(
            {
                'name': 'Partner_04',
                'of_geocoding_state': 'no_address',
                'of_precision': 'unknown',
            }
        )
        cls.partner_05 = cls.env['res.partner'].create(
            {
                'name': 'Partner_05',
                'of_geocoding_state': 'failure',
                'of_precision': 'unknown',
            }
        )
        cls.partner_06 = cls.env['res.partner'].create(
            {
                'name': 'Partner_06',
                'of_geocoding_state': 'manual',
                'of_precision': 'manual',
                # Geo coordinates of Rennes
                'partner_latitude': float('48.1113387'),
                'partner_longitude': float('-1.6800198'),
            }
        )
        cls.partner_07 = cls.env['res.partner'].create(
            {
                'name': 'Partner_07',
                'zip': '?',
                'of_geocoding_state': 'failure',
                'of_precision': 'unknown',
                # False coordinates to check that we update the partner
                'partner_latitude': -1.0,
                'partner_longitude': -1.0,
            }
        )

        # Create waited responses of geocoding for the partners
        cls.partner_01_response = {
            'name': 'Partner_01',
            'requested_address': "1 Rue de la Terre Victoria, 35760 Saint-Grégoire, France",
            'response_address': "Rue de la Terre Victoria, Parc Edonia, Le Champ Rabey, Saint-Grégoire, Rennes, "
            "Ille-et-Vilaine, Bretagne, France métropolitaine, 35760, France",
            'of_geocoding_state': 'success',
            'of_precision': 'high',
        }
        cls.partner_02_response = {
            'name': 'Partner_02',
            'requested_address': "35000 Rennes, France",
            'response_address': "Rennes, Ille-et-Vilaine, Bretagne, France métropolitaine, France",
            'of_geocoding_state': 'success',
            'of_precision': 'low',
        }

    def test_01_get_partners_ids(self):
        """Test the method _get_partner_ids, all partner_ids given into context should be returned as res.partner"""
        partner_ids = [self.partner_01.id, self.partner_02.id]
        partners = (
            self.env['of.geo.wizard']
            .with_context(active_model='res.partner', active_ids=partner_ids)
            ._get_partner_ids()
        )
        self.assertEqual(len(partners), 2)
        self.assertEqual(partners, self.env['res.partner'].browse(partner_ids))

    def test_02_wizard_opening(self):
        """Test the wizard opening with partner_ids"""

        # same partner_ids in context, we should have only one partner in the wizard
        wizard = (
            self.env['of.geo.wizard']
            .with_context(active_model='res.partner', active_ids=[self.partner_01.id, self.partner_01.id])
            .create({})
        )
        self.assertEqual(len(wizard.partner_ids), 1)

        # different partner_ids in context, we should have all partners in the wizard
        partner_ids = [self.partner_01.id, self.partner_02.id]
        geo_wizard = (
            self.env['of.geo.wizard'].with_context(active_model='res.partner', active_ids=partner_ids).create({})
        )
        self.assertEqual(len(geo_wizard.partner_ids), 2)

    # test the process ;from the 1st wizard until validation (except status in ['success', 'no_address'])
    def test_03_create_lines_in_of_geo_wizard(self):
        """Test the process of geolocation with the option : update_all_selected_partners = False."""
        partner_ids = [
            self.partner_01.id,
            self.partner_02.id,
            self.partner_03.id,
            self.partner_04.id,
        ]

        # create the wizard with 4 partners
        geo_wizard = self.env['of.geo.wizard'].browse()
        geo_wizard_form = Form(
            self.env['of.geo.wizard'].with_context(active_model='res.partner', active_ids=partner_ids).create({})
        )
        geo_wizard = geo_wizard_form.save()

        # check that we have all partners in the wizard
        self.assertEqual(len(geo_wizard.partner_ids), 4)
        self.assertEqual(geo_wizard.partner_ids, self.env['res.partner'].browse(partner_ids))

        with patch.object(
            OFGeoWizard,
            '_geo_localize',
            side_effect=side_effects_test_03(),
        ):
            geo_wizard.action_button_geolocalize()

        # test the response after the geolocation of the 1st partner
        self.assertEqual(geo_wizard.line_ids[0].partner_id.name, self.partner_01_response['name'])
        self.assertEqual(geo_wizard.line_ids[0].requested_address, self.partner_01_response['requested_address'])
        self.assertEqual(geo_wizard.line_ids[0].response_address, self.partner_01_response['response_address'])
        self.assertEqual(geo_wizard.line_ids[0].geocoding_state, self.partner_01_response['of_geocoding_state'])
        self.assertEqual(geo_wizard.line_ids[0].precision, self.partner_01_response['of_precision'])

        # test the second partner
        self.assertEqual(geo_wizard.line_ids[1].partner_id.name, self.partner_02_response['name'])
        self.assertEqual(geo_wizard.line_ids[1].requested_address, self.partner_02_response['requested_address'])
        self.assertEqual(geo_wizard.line_ids[1].response_address, self.partner_02_response['response_address'])
        self.assertEqual(geo_wizard.line_ids[1].geocoding_state, self.partner_02_response['of_geocoding_state'])
        self.assertEqual(geo_wizard.line_ids[1].precision, self.partner_02_response['of_precision'])

        # check that the 3rd partner is not geolocalized because of the status already set to 'success'
        self.assertEqual(len(geo_wizard.line_ids), 2)
        self.assertEqual(geo_wizard.line_ids[0].partner_id, self.partner_01)
        self.assertEqual(geo_wizard.line_ids[1].partner_id, self.partner_02)

        # validate and write data on partners
        geo_wizard.action_button_validate()

        # Only the 1st and 2nd partner should be updated
        self.assertEqual(self.partner_01.of_precision, self.partner_01_response['of_precision'])
        self.assertEqual(self.partner_01.of_geocoding_state, self.partner_01_response['of_geocoding_state'])
        self.assertEqual(self.partner_02.of_precision, self.partner_02_response['of_precision'])
        self.assertEqual(self.partner_02.of_geocoding_state, self.partner_02_response['of_geocoding_state'])

    def test_04_update_all_selected_partners(self):
        """Test the process with the option : update_all_selected_partners = True.
        All partners should be geolocalized except those without an address (self.partner_04).
        Also check that we update the 2 partners (self.partner_01 and self.partner_03).
        """
        partner_ids = [self.partner_02.id, self.partner_01.id, self.partner_04.id]

        geo_wizard = self.env['of.geo.wizard'].browse()
        with Form(
            self.env['of.geo.wizard'].with_context(active_model='res.partner', active_ids=partner_ids).create({})
        ) as geo_wizard_form:
            geo_wizard_form.update_all_selected = True
            geo_wizard_form.update_also_failed = False
            geo_wizard = geo_wizard_form.save()

        # check that we have all partners in the wizard
        self.assertEqual(len(geo_wizard.partner_ids), 3)
        self.assertEqual(geo_wizard.partner_ids, self.env['res.partner'].browse(partner_ids))

        with patch.object(
            OFGeoWizard,
            '_geo_localize',
            side_effect=side_effects_test_04(),
        ):
            geo_wizard.action_button_geolocalize()

        # Check that we geolocate all customers, except those without an address (self.partner_04)
        self.assertEqual(len(geo_wizard.line_ids), 2)
        self.assertEqual(geo_wizard.line_ids[0].partner_id, self.partner_01)
        self.assertEqual(geo_wizard.line_ids[1].partner_id, self.partner_02)

        # validate the geolocation
        geo_wizard.action_button_validate()

        # Check that we update the 2 partners
        self.assertEqual(self.partner_01.of_precision, self.partner_01_response['of_precision'])
        self.assertEqual(self.partner_01.of_geocoding_state, self.partner_01_response['of_geocoding_state'])
        self.assertEqual(self.partner_03.of_precision, self.partner_03['of_precision'])
        self.assertEqual(self.partner_03.of_geocoding_state, self.partner_03['of_geocoding_state'])

    def test_05_update_all_selected_partners_with_failed_geo_partners(self):
        """Test the geolocation with the options :  update_all = True and update failure = True."""
        partner_ids = [self.partner_01.id, self.partner_03.id, self.partner_05.id]

        geo_wizard = self.env['of.geo.wizard'].browse()
        with Form(
            self.env['of.geo.wizard'].with_context(active_model='res.partner', active_ids=partner_ids).create({})
        ) as geo_wizard_form:
            geo_wizard_form.update_all_selected = True
            geo_wizard_form.update_also_failed = True
            geo_wizard = geo_wizard_form.save()

        # Check that we have all partners in the wizard
        self.assertEqual(len(geo_wizard.partner_ids), 3)
        self.assertEqual(geo_wizard.partner_ids, self.env['res.partner'].browse(partner_ids))

        with patch.object(
            OFGeoWizard,
            '_geo_localize',
            side_effect=side_effects_test_05(),
        ):
            geo_wizard.action_button_geolocalize()

        # Add a new line in the wizard
        geo_wizard.line_ids = [
            Command.create(
                {
                    'partner_id': self.partner_07.id,
                    'requested_address': self.partner_07.zip,
                    'geocoding_state': self.partner_07.of_geocoding_state,
                    'precision': self.partner_07.of_precision,
                }
            )
        ]

        geo_wizard.action_button_validate()

        # check that we save the informations of failed geolocation
        self.assertEqual(self.partner_07.of_geocoding_state, 'no_address')
        self.assertEqual(self.partner_07.of_precision, 'unknown')
        self.assertEqual(self.partner_07.partner_latitude, 0.0)
        self.assertEqual(self.partner_07.partner_longitude, 0.0)

    def test_06_update_all_except_manual(self):
        """Test the geolocation with the option : update_all_except_manual = True.
        All partners should be geolocalized except those with a manual status (self.partner_06).
        """
        partner_ids = [self.partner_06.id, self.partner_02.id, self.partner_01.id]
        geo_wizard = self.env['of.geo.wizard'].browse()

        with Form(
            self.env['of.geo.wizard'].with_context(active_model='res.partner', active_ids=partner_ids).create({})
        ) as geo_wizard_form:
            geo_wizard_form.update_all_selected_except_manual_geolocalized = True
            geo_wizard_form.update_also_failed = False
            geo_wizard = geo_wizard_form.save()

        self.assertEqual(len(geo_wizard.partner_ids), 3)
        self.assertEqual(geo_wizard.partner_ids, self.env['res.partner'].browse(partner_ids))

        with patch.object(
            OFGeoWizard,
            '_geo_localize',
            side_effect=side_effects_test_06(),
        ):
            geo_wizard.action_button_geolocalize()

        self.assertEqual(len(geo_wizard.line_ids), 2)
        self.assertEqual(geo_wizard.line_ids[0].partner_id, self.partner_01)
        self.assertEqual(geo_wizard.line_ids[1].partner_id, self.partner_02)

    def test_07_update_all_except_manual_with_failed_geo_partners(self):
        """Test the geolocation with the option : update_all_except_manual = True and update_failure = True.
        All partners should be geolocalized also those with a failure status (self.partner_07) and the manual
        status (self.partner_06).
        """
        partner_ids = [self.partner_03.id, self.partner_02.id, self.partner_06.id]

        with Form(
            self.env['of.geo.wizard'].with_context(active_model='res.partner', active_ids=partner_ids).create({})
        ) as geo_wizard_form:
            geo_wizard_form.update_all_selected_except_manual_geolocalized = True
            geo_wizard_form.update_also_failed = True
            geo_wizard = geo_wizard_form.save()

        self.assertEqual(len(geo_wizard.partner_ids), 3)
        self.assertEqual(geo_wizard.partner_ids, self.env['res.partner'].browse(partner_ids))

        with patch.object(
            OFGeoWizard,
            '_geo_localize',
            side_effect=side_effects_test_07(),
        ):
            geo_wizard.action_button_geolocalize()

        self.assertEqual(len(geo_wizard.line_ids), 2)
        self.assertEqual(geo_wizard.line_ids[0].partner_id, self.partner_02)
        self.assertEqual(geo_wizard.line_ids[1].partner_id, self.partner_03)

        # Add a new line in the wizard. We will not use Form() here because `partner_id` is in readonly. We can't add
        # a new line with the wizard form after geolocalization.
        geo_wizard.line_ids = [
            Command.create(
                {
                    'partner_id': self.partner_07.id,
                    'requested_address': self.partner_07.zip,
                    'geocoding_state': self.partner_07.of_geocoding_state,
                    'precision': self.partner_07.of_precision,
                }
            )
        ]

        geo_wizard.action_button_validate()

        # check that we save the informations of failed geolocation
        self.assertEqual(self.partner_07.of_geocoding_state, 'no_address')
        self.assertEqual(self.partner_07.of_precision, 'unknown')
        self.assertEqual(self.partner_07.partner_latitude, 0.0)
        self.assertEqual(self.partner_07.partner_longitude, 0.0)
