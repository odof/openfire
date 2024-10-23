# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def _delete_existing_fields_selection(cr):
    cr.execute(
        """DELETE FROM IR_MODEL_FIELDS_SELECTION
WHERE
    FIELD_ID IN (
        SELECT
            ID
        FROM
            IR_MODEL_FIELDS
        WHERE
            MODEL = 'of.connector.config.settings'
    )"""
    )


def pre_init_hook(cr):
    """activate the settings view of the base module."""
    _delete_existing_fields_selection(cr)
