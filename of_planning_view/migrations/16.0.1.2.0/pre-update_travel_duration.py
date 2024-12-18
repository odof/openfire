# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    cr.execute(
        """
        DO $$
        BEGIN
            -- Vérifier si la colonne of_trip_duration existe
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'calendar_event'
                  AND column_name = 'of_trip_duration'
            ) THEN
                -- Mettre à jour la colonne of_travel_duration
                UPDATE calendar_event
                SET of_travel_duration = of_trip_duration;
            END IF;
        END $$;
    """
    )
