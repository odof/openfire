# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

LATITUDE_RENNES = "48.1113387"
LONGITUDE_RENNES = "-1.6800198"

LATITUDE_SAINT_GREGOIRE = "48.1513003"
LONGITUDE_SAINT_GREGOIRE = "-1.6985415"


@tagged("post_install", "-at_install", "openfire_custom")
class TestModuleOfGeolocalize(TransactionCase):
    def test_01_geolocalize_settings_values_create_no_write_no(self):
        """Test the default values of the settings. Partner should not be geolocalized on create and on write."""
        partner = self.env['res.partner'].create(
            {
                "name": "Test_01",
                "zip": "35000",
                "city": "rennes",
            }
        )
        self.assertEqual(partner.partner_latitude, 0.0)
        self.assertEqual(partner.partner_longitude, 0.0)
        self.assertEqual(partner.of_geocoding_state, 'not_tried')
        partner.update(
            {
                'zip': '35760',
                'street': '1 Rue de la Terre Victoria',
            }
        )
        self.assertEqual(partner.partner_latitude, 0.0)
        self.assertEqual(partner.partner_longitude, 0.0)
        self.assertEqual(partner.of_geocoding_state, 'not_tried')

    def test_02_geolocalize_settings_values_create_yes_write_yes(self):
        """Partner should be geolocalized on create and on write."""

        # Set the settings values
        self.env['res.config.settings'].create(
            {
                "geocoding_on_write": 'yes',
                "geocoding_on_create": 'yes',
            }
        ).execute()

        # We mock the call to the API
        with patch(
            'odoo.addons.of_geolocalize.models.base_geocoder.GeoCoder._call_openstreetmap'
        ) as mock_call_openstreetmap:
            mock_call_openstreetmap.return_value = [
                LATITUDE_RENNES,
                LONGITUDE_RENNES,
                [
                    {
                        'place_id': 245190588,
                        'licence': 'Data © OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright',
                        'osm_type': 'relation',
                        'osm_id': 54517,
                        'lat': '48.1113387',
                        'lon': '-1.6800198',
                        'class': 'boundary',
                        'type': 'administrative',
                        'place_rank': 16,
                        'importance': 0.6251117378386865,
                        'addresstype': 'city',
                        'name': 'Rennes',
                        'display_name': 'Rennes, Ille-et-Vilaine, Bretagne, France métropolitaine, France',
                        'boundingbox': ['48.0769155', '48.1549705', '-1.7525876', '-1.6244045'],
                    }
                ],
            ]

            # Create the partner
            partner = (
                self.env['res.partner']
                .with_context(force_geo_localize=True)
                .create(
                    {
                        'name': 'Test_02',
                        'zip': '35000',
                        'city': 'rennes',
                    }
                )
            )
            self.assertEqual(partner.partner_latitude, float(LATITUDE_RENNES))
            self.assertEqual(partner.partner_longitude, float(LONGITUDE_RENNES))
            self.assertNotEqual(partner.of_geocoding_state, 'not_tried')
            self.assertEqual(partner.of_geocoding_state, 'success')

            # Update the partner
            partner.update(
                {
                    'zip': '35760',
                    'street': '1 Rue de la Terre Victoria',
                }
            )
            self.assertNotEqual(partner.partner_latitude, float(LATITUDE_SAINT_GREGOIRE))
            self.assertNotEqual(partner.partner_longitude, float(LONGITUDE_SAINT_GREGOIRE))
            self.assertEqual(partner.of_geocoding_state, 'success')
            self.assertIsNotNone(partner.of_response_json)

    def test_03_geolocalize_settings_values_create_yes_write_no(self):
        """Partner should be geolocalized on write but not on create."""

        # Set the settings values
        self.env['res.config.settings'].create(
            {
                'geocoding_on_write': 'yes',
                'geocoding_on_create': 'no',
            }
        ).execute()

        # We mock the call to the API
        with patch(
            'odoo.addons.of_geolocalize.models.base_geocoder.GeoCoder._call_openstreetmap'
        ) as mock_call_openstreetmap:
            mock_call_openstreetmap.return_value = [
                LATITUDE_SAINT_GREGOIRE,
                LONGITUDE_SAINT_GREGOIRE,
                [
                    {
                        "place_id": 245342690,
                        "licence": "Data © OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright",
                        "osm_type": "way",
                        "osm_id": 490952741,
                        "lat": "48.1513003",
                        "lon": "-1.6985415",
                        "class": "highway",
                        "type": "unclassified",
                        "place_rank": 26,
                        "importance": 0.10000999999999993,
                        "addresstype": "road",
                        "name": "Rue de la Terre Victoria",
                        "display_name": "Rue de la Terre Victoria, Parc Edonia, Le Champ Rabey,\
                        Saint-Grégoire, Rennes, Ille-et-Vilaine, Bretagne, France métropolitaine, 35760, France",
                        "boundingbox": ["48.1494328", "48.1529138", "-1.6987829", "-1.6970011"],
                    }
                ],
            ]

            # Create the partner, it should not be geolocalized because of the settings
            partner = (
                self.env['res.partner']
                .with_context(force_geo_localize=True)
                .create(
                    {
                        'name': 'Test_03',
                        'zip': '35000',
                        'city': 'rennes',
                    }
                )
            )
            self.assertEqual(partner.partner_latitude, 0.0)
            self.assertEqual(partner.partner_longitude, 0.0)
            self.assertEqual(partner.of_geocoding_state, 'not_tried')

            # Update the partner, it should be geolocalized because of the settings
            partner.update(
                {
                    'zip': '35760',
                    'street': '1 Rue de la Terre Victoria',
                }
            )
            self.assertEqual(round(partner.partner_latitude, 7), float(LATITUDE_SAINT_GREGOIRE))
            self.assertEqual(round(partner.partner_longitude, 7), float(LONGITUDE_SAINT_GREGOIRE))
            self.assertNotEqual(partner.of_geocoding_state, 'not_tried')
            self.assertEqual(partner.of_geocoding_state, 'success')

    def test_04_geolocalize_settings_values_create_no_write_yes(self):
        """Partner should be geolocalized on create but not on write."""

        self.env['res.config.settings'].create(
            {
                'geocoding_on_write': 'no',
                'geocoding_on_create': 'yes',
            }
        ).execute()

        # We mock the call to the API
        with patch(
            'odoo.addons.of_geolocalize.models.base_geocoder.GeoCoder._call_openstreetmap'
        ) as mock_call_openstreetmap:
            mock_call_openstreetmap.return_value = [
                LATITUDE_RENNES,
                LONGITUDE_RENNES,
                [
                    {
                        'place_id': 245190588,
                        'licence': 'Data © OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright',
                        'osm_type': 'relation',
                        'osm_id': 54517,
                        'lat': '48.1113387',
                        'lon': '-1.6800198',
                        'class': 'boundary',
                        'type': 'administrative',
                        'place_rank': 16,
                        'importance': 0.6251117378386865,
                        'addresstype': 'city',
                        'name': 'Rennes',
                        'display_name': 'Rennes, Ille-et-Vilaine, Bretagne, France métropolitaine, France',
                        'boundingbox': ['48.0769155', '48.1549705', '-1.7525876', '-1.6244045'],
                    }
                ],
            ]

            # Create the partner, it should be geolocalized because of the settings
            partner = (
                self.env['res.partner']
                .with_context(force_geo_localize=True)
                .create(
                    {
                        'name': 'Test_04',
                        'zip': '35000',
                        'city': 'rennes',
                    }
                )
            )
            self.assertEqual(partner.partner_latitude, float(LATITUDE_RENNES))
            self.assertEqual(partner.partner_longitude, float(LONGITUDE_RENNES))
            self.assertNotEqual(partner.partner_longitude, 'not_tried')

            # Update the partner, it should not be geolocalized because of the settings
            partner.update(
                {
                    'street': '1 Rue de la Terre Victoria',
                    'zip': '35760',
                }
            )

            # Geodata will be reset to 0.0 because the settings is set to 'no' for geolocalization on write
            self.assertEqual(partner.partner_latitude, 0.0)
            self.assertEqual(partner.partner_longitude, 0.0)
            self.assertEqual(partner.of_geocoding_state, 'success')
