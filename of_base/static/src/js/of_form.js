odoo.define('of_base.FormView', function(require) {
"use strict";

var core = require('web.core');
var session = require('web.session');

var _t = core._t;

var FormView = require('web.FormView');
var Model = require('web.Model');

FormView.include({
   // Redéfinition de la fonction standard
   // Fonction appelée lors de la sauvegarde d'un form "classique"
    on_button_save: function() {
        var self = this;
        if (this.is_disabled) {
            return;
        }
        this.disable_button();
        // On teste si on est en mode création
        var creation = false;
        if (!self.datarecord.id) {
            creation = true;
        }
        return this.save().then(function(result) {
            self.trigger("save", result);
            return self.reload().then(function() {
                self.to_view_mode();
                core.bus.trigger('do_reload_needaction');
                core.bus.trigger('form_view_saved', self);
            }).always(function() {
                self.enable_button();
                // Contrôle des doublons potentiels lors de la création d'un nouveau contact
                if (creation && self.model === 'res.partner' && typeof self.datarecord.id != "string") {
                    new Model('res.partner').call('check_duplications', [self.datarecord.id]).done(function (res) {
                        if (res[0]) {
                            self.do_action({
                                type: 'ir.actions.act_window',
                                name: 'ATTENTION',
                                res_model: 'of.res.partner.check.duplications',
                                view_mode: 'form',
                                view_type: 'form',
                                views: [[false,'form']],
                                target: 'new',
                                context: {'default_duplication_ids': res[0],
                                          'default_new_partner_id': self.datarecord.id},
                            });
                        }
                    });
                }
                // Contrôle des doublons potentiels lors de la création d'une nouvelle opportunité
                else if (creation && self.model === 'crm.lead' && self.datarecord.of_check_duplications && typeof self.datarecord.partner_id[0] != "string") {
                    new Model('res.partner').call('check_duplications', [self.datarecord.partner_id[0]]).done(function (res) {
                        if (res[0]) {
                            self.do_action({
                                type: 'ir.actions.act_window',
                                name: 'ATTENTION',
                                res_model: 'of.res.partner.check.duplications',
                                view_mode: 'form',
                                view_type: 'form',
                                views: [[false,'form']],
                                target: 'new',
                                context: {'default_duplication_ids': res[0],
                                          'default_new_partner_id': self.datarecord.partner_id[0]},
                            });
                        }
                    });
                }
            });
        }).fail(function(){
            self.enable_button();
        });
    },
});

return FormView;

});

odoo.define('of_base.FormViewDialog', function(require) {
"use strict";

var core = require('web.core');
var session = require('web.session');

var _t = core._t;

var form_common = require('web.form_common');
var Model = require('web.Model');

form_common.FormViewDialog.include({
    // Redéfinition de la fonction standard
    // Fonction appelée lors de la sauvegarde d'un form popup
    init: function(parent, options) {
        var self = this;
        var parent_view = parent;
        var multi_select = !_.isNumber(options.res_id) && !options.disable_multiple_selection;
        var readonly = _.isNumber(options.res_id) && options.readonly;

        if(!options || !options.buttons) {
            options = options || {};
            options.buttons = [
                {text: (readonly ? _t("Close") : _t("Discard")), classes: "btn-default o_form_button_cancel", close: true, click: function() {
                    self.view_form.trigger('on_button_cancel');
                }}
            ];

            if(!readonly) {
                // Partie appelée lors de la sauvegarde via bouton "Sauvegarder et Fermer"
                options.buttons.splice(0, 0, {text: _t("Save") + ((multi_select)? " " + _t(" & Close") : ""), classes: "btn-primary", click: function() {
                    self.view_form.onchanges_mutex.def.then(function() {
                        if (!self.view_form.warning_displayed) {
                            // On teste si on est en mode création
                            var creation = false;
                            if (!self.view_form.datarecord.id) {
                                creation = true;
                            }
                            $.when(self.view_form.save()).done(function() {
                                self.view_form.reload_mutex.exec(function() {
                                    self.trigger('record_saved');
                                    self.close();
                                    // Contrôle des doublons potentiels lors de la création d'un nouveau contact
                                    if (creation && self.view_form.model === 'res.partner' && typeof self.view_form.datarecord.id != "string") {
                                        new Model('res.partner').call('check_duplications', [self.view_form.datarecord.id]).done(function (res) {
                                            if (res[0]) {
                                                parent_view.do_action({
                                                    type: 'ir.actions.act_window',
                                                    name: 'ATTENTION',
                                                    res_model: 'of.res.partner.check.duplications',
                                                    view_mode: 'form',
                                                    view_type: 'form',
                                                    views: [[false,'form']],
                                                    target: 'new',
                                                    context: {'default_duplication_ids': res[0],
                                                              'default_new_partner_id': self.view_form.datarecord.id},
                                                });
                                            }
                                        });
                                    }
                                    // Contrôle des doublons potentiels lors de la création d'une nouvelle opportunité
                                    else if (creation && self.view_form.model === 'crm.lead' && self.view_form.datarecord.of_check_duplications && typeof self.view_form.datarecord.partner_id[0] != "string") {
                                        new Model('res.partner').call('check_duplications', [self.view_form.datarecord.partner_id[0]]).done(function (res) {
                                            if (res[0]) {
                                                parent_view.do_action({
                                                    type: 'ir.actions.act_window',
                                                    name: 'ATTENTION',
                                                    res_model: 'of.res.partner.check.duplications',
                                                    view_mode: 'form',
                                                    view_type: 'form',
                                                    views: [[false,'form']],
                                                    target: 'new',
                                                    context: {'default_duplication_ids': res[0],
                                                              'default_new_partner_id': self.view_form.datarecord.partner_id[0]},
                                                });
                                            }
                                        });
                                    }
                                });
                            });
                        }
                    });
                }});

                // Partie appelée lors de la sauvegarde via bouton "Enregistrer et créer"
                if(multi_select) {
                    options.buttons.splice(1, 0, {text: _t("Save & New"), classes: "btn-primary", click: function() {
                        // On teste si on est en mode création
                        var creation = false;
                        if (!self.view_form.datarecord.id) {
                            creation = true;
                        }
                        $.when(self.view_form.save()).done(function() {
                            self.view_form.reload_mutex.exec(function() {
                                self.view_form.on_button_new();
                                // Contrôle des doublons potentiels lors de la création d'un nouveau contact
                                if (creation && self.view_form.model === 'res.partner' && typeof self.view_form.datarecord.id != "string") {
                                    new Model('res.partner').call('check_duplications', [self.view_form.datarecord.id]).done(function (res) {
                                        if (res[0]) {
                                            self.view_form.do_action({
                                                type: 'ir.actions.act_window',
                                                name: 'ATTENTION',
                                                res_model: 'of.res.partner.check.duplications',
                                                view_mode: 'form',
                                                view_type: 'form',
                                                views: [[false,'form']],
                                                target: 'new',
                                                context: {'default_duplication_ids': res[0],
                                                          'default_new_partner_id': self.view_form.datarecord.id},
                                            });
                                        }
                                    });
                                }
                                // Contrôle des doublons potentiels lors de la création d'une nouvelle opportunité
                                else if (creation && self.view_form.model === 'crm.lead' && self.view_form.datarecord.of_check_duplications && typeof self.view_form.datarecord.partner_id[0] != "string") {
                                    new Model('res.partner').call('check_duplications', [self.view_form.datarecord.partner_id[0]]).done(function (res) {
                                        if (res[0]) {
                                            self.view_form.do_action({
                                                type: 'ir.actions.act_window',
                                                name: 'ATTENTION',
                                                res_model: 'of.res.partner.check.duplications',
                                                view_mode: 'form',
                                                view_type: 'form',
                                                views: [[false,'form']],
                                                target: 'new',
                                                context: {'default_duplication_ids': res[0],
                                                          'default_new_partner_id': self.view_form.datarecord.partner_id[0]},
                                            });
                                        }
                                    });
                                }
                            });
                        });
                    }});
                }
            }
        }

        this._super(parent, options);
    },
});

return form_common.FormViewDialog;

});

odoo.define('of_base.WidgetButton', function(require) {
"use strict";

var core = require('web.core');
var session = require('web.session');

var _t = core._t;

var form_widgets = require('web.form_widgets');
var Model = require('web.Model');

form_widgets.WidgetButton.include({
   // Redéfinition de la fonction standard
    on_click: function() {
        var self = this;
        if (this.view.is_disabled) {
            return;
        }
        this.force_disabled = true;
        this.check_disable();
        this.view.disable_button();
        // On teste si on est en mode création
        var creation = false;
        if (!self.view.datarecord.id) {
            creation = true;
        }
        this.execute_action().always(function() {
            self.view.enable_button();
            self.force_disabled = false;
            self.check_disable();
            if (self.$el.hasClass('o_wow')) {
                self.show_wow();
            }
            // Contrôle des doublons potentiels lors de la création d'un nouveau contact
            if (creation && self.view.model === 'res.partner' && typeof self.view.datarecord.id != "string") {
                new Model('res.partner').call('check_duplications', [self.view.datarecord.id]).done(function (res) {
                    if (res[0]) {
                        self.view.ViewManager.action_manager.do_action({
                            type: 'ir.actions.act_window',
                            name: 'ATTENTION',
                            res_model: 'of.res.partner.check.duplications',
                            view_mode: 'form',
                            view_type: 'form',
                            views: [[false,'form']],
                            target: 'new',
                            context: {'default_duplication_ids': res[0],
                                      'default_new_partner_id': self.view.datarecord.id},
                        });
                    }
                });
            }
            // Contrôle des doublons potentiels lors de la création d'une nouvelle opportunité
            else if (creation && self.view.model === 'crm.lead' && self.view.datarecord.of_check_duplications && typeof self.view.datarecord.partner_id[0] != "string") {
                new Model('res.partner').call('check_duplications', [self.view.datarecord.partner_id[0]]).done(function (res) {
                    if (res[0]) {
                        self.view.ViewManager.action_manager.do_action({
                            type: 'ir.actions.act_window',
                            name: 'ATTENTION',
                            res_model: 'of.res.partner.check.duplications',
                            view_mode: 'form',
                            view_type: 'form',
                            views: [[false,'form']],
                            target: 'new',
                            context: {'default_duplication_ids': res[0],
                                      'default_new_partner_id': self.view.datarecord.partner_id[0]},
                        });
                    }
                });
            }
        });
    },

});

return form_widgets.WidgetButton;

});
