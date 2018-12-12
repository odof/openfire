/*
* @Author: D.Jane
* @Email: jane.odoo.sp@gmail.com
* */
odoo.define('list_editor.main', function (require) {
    "use strict";
    var session = require('web.session');
    var Model = require('web.Model');
    var ListView = require('web.ListView');

    var _super_reload_content = ListView.prototype.reload_content;
    ListView.include({
        reload_content: function () {
            var self = this;
            var done = $.Deferred();
            var key = this.get_key_when_loading();

            if (key) {
                new Model('list.editor').call('get_list_view', [key]).then(function (res) {
                    if (res) {
                        self.replace_view(res);
                    }
                    _super_reload_content.apply(self).then(function () {
                        if (self.model !== 'ir.model.fields'){
                            self.init_edit_button(self.$el);
                        }
                        done.resolve();
                    });
                });
            } else {
                _super_reload_content.apply(self).then(function () {
                    if (self.model !== 'ir.model.fields'){
                        self.init_edit_button(self.$el);
                    }
                    done.resolve();
                });
            }
            return done;
        },
        get_key_when_loading: function () {
            // get key when action still haven't done,so can't get key from url
            if (this.ViewManager.action_manager) {
                if (!this.ViewManager.action.res_model || !this.ViewManager.action.id) {
                    return false;
                }
                else {
                    return 'list' + this.ViewManager.action.res_model + this.ViewManager.action.id + this.model;
                }

            } else {
                // x2m and wizard always can get key from url
                return this.get_key();
            }
        },
        init_edit_button: function ($container) {
            if (!session.debug || !localStorage.getItem('list_editor')) {
                return false;
            }
            $container.prepend('<button class="btn btn-sm btn-icon fa fa-edit list-editor" ' +
                'style="margin: 4px; padding: 2px 6px;"/>');
            $container.children('.list-editor').on('click', this.open_list_editor.bind(this));
            return true;
        },
        replace_view: function (view) {
            var self = this;
            // editable
            if (this.fields_view.arch.attrs['editable'] !== view.editable && view.editable) {
                this.fields_view.arch.attrs['editable'] = view.editable;
                if (this.editable() && this.$buttons) {
                    this.$buttons
                        .off('click', '.o_list_button_save')
                        .on('click', '.o_list_button_save', this.proxy('save_edition'))
                        .off('click', '.o_list_button_discard')
                        .on('click', '.o_list_button_discard', function (e) {
                            e.preventDefault();
                            self.cancel_edition();
                        });
                }
            }

             // fields
            _.mapObject(view['new_fields'], function (val, key) {
                self.fields_get[key] = val;
            });

            // add column to arch and re-order
            var j = 0;
            _.each(view['visible_columns'], function (name) {
                var i = self.fields_view.arch.children.map(function (item) {
                    return item.attrs.name;
                }).indexOf(name);
                if (i === -1) {
                    var attrs;
                    if (self.fields_get[name].type === "many2many" || self.fields_get[name].type === "one2many") {
                        attrs = {name: name, modifiers: "{}", widget: "many2many_tags"};
                    }else {
                        attrs = {name: name, modifiers: "{}"};
                    }
                    self.fields_view.arch.children.splice(j, 0, {
                        tag: 'field', attrs: attrs
                    });
                    self.fields_view.fields[name] = _.extend(self.fields_get[name], attrs);
                    j += 1;
                } else {
                    var column = self.fields_view.arch.children[i];

                    // make visible if column is invisible
                    self.make_visible_column(column);

                    self.fields_view.arch.children.splice(i, 1);
                    if (j > i) {
                        j -= 1;
                    }
                    self.fields_view.arch.children.splice(j, 0, column);
                    j += 1;
                }
            });

            // make invisible
            self.fields_view.arch.children.forEach(function (item) {
                var name = item.attrs.name;
                if (view['visible_columns'].indexOf(name) === -1) {
                    self.make_invisible_column(item);
                }
            });
        },
        make_visible_column: function (column) {
            if (column.attrs.modifiers) {
                var modifiers = JSON.parse(column.attrs.modifiers);
                delete modifiers['tree_invisible'];
                column.attrs.modifiers = JSON.stringify(modifiers);
            }
        },
        make_invisible_column: function (column) {
            if (column.attrs.modifiers) {
                var modifiers = JSON.parse(column.attrs.modifiers);
                modifiers['tree_invisible'] = true;
                column.attrs.modifiers = JSON.stringify(modifiers);
            }
        },
        open_list_editor: function () {
            var key = this.get_key();

            if (!key) {
                return;
            }

            var self = this;
            new Model('list.editor').call('open_list_editor', [key]).then(function (res) {
                if (res['open_for_create']) {
                    self.open_for_create(res['view_id']);
                } else {
                    self.do_action(res).then(function () {
                        self.register_change_event();
                    });
                }
            })
        },
        register_change_event: function () {
            var self = this;
            var $modal = $('.modal.in');
            $modal.find('button.change').on('click', function () {
                if (self.get_type() === 'wizard') {
                    self.do_action({type: 'ir.actions.act_window_close'});
                } else {
                    $modal.modal('hide');
                }
                self.reload_content();
            });
        },
        open_for_create: function (view_id) {
            var self = this;
            var action = {
                type: 'ir.actions.act_window',
                name: 'List Editor',
                res_model: 'list.editor',
                views: [[view_id, 'form']],
                view_type: "form",
                view_mode: "form",
                target: 'new'
            };

            var default_visible_columns = this.visible_columns.map(function (item) {
                return item.name;
            }).join(',');

            this.get_visible_fields_ids().then(function (res) {
                action['context'] = {
                    default_full_key: self.get_full_key(),
                    default_model_id: res['model_id'],
                    default_default_visible_columns: default_visible_columns,
                    default_visible_fields: res['visible_ids'],
                    default_editable: self.fields_view.arch.attrs.editable || false
                };
                self.do_action(action).then(function () {
                    self.register_change_event();
                });
            });
        },
        get_visible_fields_ids: function () {
            var def = $.Deferred();

            var visible_fields = this.visible_columns.map(function (item) {
                return item.name;
            });

            new Model('list.editor')
                .call('get_visible_fields_ids', [this.model, visible_fields])
                .then(function (res) {
                    if (res) {
                        def.resolve(res);
                    } else {
                        def.reject();
                    }
                });
            return def.promise();
        },
        get_key: function () {
            var type = this.get_type();
            var model = this.get_current_model();
            var action = this.get_current_action();

            if (!type || !model || !action) {
                return false;
            }

            return type + model + action + this.model;
        },
        get_full_key: function () {
            return this.get_key() + session.user_context.uid;
        },
        get_current_action: function () {
            var action = /action=(\d+)/g.exec(window.location.href);
            if (!action) {
                return false;
            }
            return action[1];
        },
        get_current_model: function () {
            var model = /model=([A-Za-z0-9_.]+)/g.exec(window.location.href);
            if (!model) {
                return false;
            }
            return model[1];
        },
        get_type: function () {
            if (this.x2m) {
                return 'x2m'
            } else if (this.ViewManager.$modal) {
                return 'wizard'
            } else if (this.ViewManager.action_manager) {
                return 'list'
            } else {
                return false;
            }
        }
    });
});
