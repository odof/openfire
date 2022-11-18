odoo.define('web_confirm_on_save.web_confirm_on_save', function (require) {
"use strict";

var FormView = require('web.FormView');
var Model = require('web.DataModel');

var Dialog = require('web.Dialog');

FormView.include({

    check_condition: function (modelName, record_id ,data_changed) {
        var def = this.dataset._model.call("check_condition_show_dialog",[record_id ,data_changed]);
        return def;
    },

    checkCanBeSaved: function (recordID) {
        var fieldNames = this.renderer.canBeSaved(recordID || this.handle);
        if (fieldNames.length) {
            return false;
        }
        return true;
    },

    willStart: function() {
        var self = this;
        var my_model = new Model(this.dataset._model.name);
        var dialog_type = my_model.call('dialog_type',[]);
        return $.when(dialog_type, this._super()).then(function (dialog_type) {
            self.dialog_type = dialog_type
        }

        )
    },

    on_button_save: function (ev) {
        var self = this;
        var my_function = this._super
        var modelName = this.dataset._model.name;
        var data_changed = this.datarecord;
        var values = {}
        var readonly_values = {}
        // function adapted from web/form_view.js in function _process_save
        // allows us to get values from every modified field on the form
        _.each(self.fields, function (f) {
            if (f.is_valid() && f.name !== 'id' && (!self.datarecord.id || f._dirty_flag)) {
                // Special case 'id' field, do not save this field
                // on 'create' : save all non readonly fields
                // on 'edit' : save non readonly modified fields
                if (!f.get("readonly")) {
                    values[f.name] = f.get_value(true);
                } else {
                    readonly_values[f.name] = f.get_value(true);
                }
            }

        });
        var record_id = data_changed && data_changed.id ? data_changed.id : false;
        var dialog_type = self.dialog_type;
        function saveAndExecuteAction () {
            ev.stopPropagation(); // Prevent x2m lines to be auto-saved
            my_function.apply(self, arguments);
        }
        if(modelName && dialog_type[0]){
            self.check_condition(modelName, record_id, values).then(function(opendialog){
                if(!opendialog){
                    saveAndExecuteAction();
                }else{
                    if(dialog_type[0] == 'confirm'){
                        var def = new Promise(function (resolve, reject) {
                            Dialog.confirm(self, dialog_type[1], {
                                confirm_callback: saveAndExecuteAction,
                            }).on("closed", null, resolve);
                        });
                    }else{
                        var def = new Promise(function (resolve, reject) {
                            Dialog.alert(self, dialog_type[1], {
                                confirm_callback: saveAndExecuteAction,
                            }).on("closed", null, resolve);
                        });
                        saveAndExecuteAction();
                    }
                }
            });
        }else{
            this._super();
        }
    },

});

return FormView;

});
