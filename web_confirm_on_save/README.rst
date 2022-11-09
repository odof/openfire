=========================
Web Dialog Confirm on Save
=========================

Show dialog to confirm or alert on form view after save a record:

If you want to check condition to show dialog, add these functions to model:
```python
    @api.model
    def check_condition_show_dialog(self, record_id, data):
        """
            :param:   self: current model
                      record_id: id of record if save on write function, False on create function
                      data: data from the form
            :returns: True: show dialog
                      False: ignore dialog
        """
        return False
```
Return False by default, override and return True to open a dialog.

```python
    @api.model
    def dialog_type(self):
        """
            :param self: current model.
            :returns: False, False -> No dialog
                      'confirm', "message" -> A confirmation dialog that won't save unless the user press OK
                      'alert', "message" -> An alert dialog that will warn the user and still save
        """
        return False, False
```
Return the type of dialog and displayed message.
