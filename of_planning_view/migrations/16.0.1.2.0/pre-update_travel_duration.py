# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    cr.execute(
        """
        UPDATE calendar_event
        SET of_travel_duration = of_trip_duration
    """
    )
