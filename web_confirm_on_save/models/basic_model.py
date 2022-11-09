# -*- coding: utf-8 -*-


from odoo import models, api


class BaseModel(models.AbstractModel):
    _name = 'basemodel.extension'

    @api.model_cr
    def _register_hook(self):

        # Inherit this function to decide when confirm dialog will show
        @api.model
        def check_condition_show_dialog(self, record_id, data):
            """
                :param self: current model.
                    record_id: id of record if save on write function, False on create function
                    data: data from the form
                :returns: True: show dialog
                        False: ignore dialog
            """
            return False

        # Inherit this function to decide the type of dialog and message
        @api.model
        def dialog_type(self):
            """
                :param self: current model.
                :returns: False, False -> No dialog
                          'confirm', "message" -> A confirmation dialog that won't save unless the user press OK
                          'alert', "message" -> An alert dialog that will warn the user and still save
            """
            return False, False

        # Adding the functions on BaseModel to make them available to all models
        # otherwise errors would pop up for models that do not have these functions
        models.BaseModel.check_condition_show_dialog = check_condition_show_dialog
        models.BaseModel.dialog_type = dialog_type
        return super(BaseModel, self)._register_hook()
