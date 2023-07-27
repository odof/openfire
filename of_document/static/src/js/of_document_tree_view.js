odoo.define('of_document.documents', function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var framework = require('web.framework');
    var _t = core._t;

    var Dialog = require('web.Dialog');

    var DocumentTreeView = require('muk_dms_views.documents');
    var PreviewHelper = require('muk_dms_preview_file.PreviewHelper');

    var open = function(self, model, id) {
        self.do_action({
            type: 'ir.actions.act_window',
            res_model: model,
            res_id: id,
            views: [[false, 'form']],
            target: 'current',
            context: session.user_context,
        });
    }

    var edit = function(self, model, id) {
        self.do_action({
            type: 'ir.actions.act_window',
            res_model: model,
            res_id: id,
            views: [[false, 'form']],
            target: 'current',
            flags: {'initial_mode': 'edit'},
            context: session.user_context,
        });
    }

    var download = function(self, filename, id) {
        var download_url = session.url(
            '/web/content', {
                model: 'muk_dms.file',
                filename: filename,
                filename_field: 'name',
                field: 'content',
                id: id,
                download: true
        });

        self.do_action({
            type: 'ir.actions.act_url',
            url: download_url,
            target: 'self',
        });
    }

    var create = function(self, model, parent) {
        var context = {};
        if(model == "muk_dms.file") {
            context = $.extend(session.user_context, {
                default_directory: parent
            });
        } else if(model == "muk_dms.directory") {
            context = $.extend(session.user_context, {
                default_parent_directory: parent
            });
        }
        self.do_action({
            type: 'ir.actions.act_window',
            res_model: model,
            views: [[false, 'form']],
            target: 'current',
            context: context,
        });
    }

    var context_menu_items = function(node, cp) {
        var items = {}
        if(node.data.perm_read) {
            items.open = {
                separator_before: false,
                separator_after: false,
                _disabled: false,
                icon: "fa fa-external-link-square",
                label: _t("Open"),
                action: function(data) {
                    var inst = $.jstree.reference(data.reference);
                    var obj = inst.get_node(data.reference);
                    open(inst.settings.widget, obj.data.odoo_model, obj.data.odoo_id);
                }
            };
        }
        if(node.data.perm_write) {
            items.edit = {
                separator_before: false,
                separator_after: false,
                _disabled: false,
                icon: "fa fa-pencil",
                label: _t("Edit"),
                action: function(data) {
                    var inst = $.jstree.reference(data.reference);
                    var obj = inst.get_node(data.reference);
                    edit(inst.settings.widget, obj.data.odoo_model, obj.data.odoo_id);
                }
            };
        }
        if(node.data.odoo_model == "muk_dms.file" && node.data.perm_read) {
            items.download = {
                separator_before: false,
                separator_after: false,
                _disabled: false,
                icon: "fa fa-download",
                label: _t("Download"),
                action: function(data) {
                    var inst = $.jstree.reference(data.reference);
                    var obj = inst.get_node(data.reference);
                    download(inst.settings.widget, obj.data.filename, obj.data.odoo_id);
                }
            };
        } else if(node.data.odoo_model == "muk_dms.directory" && node.data.perm_create) {
            items.create = {
                separator_before: false,
                icon: "fa fa-plus-circle",
                separator_after: false,
                label: _t("Create"),
                action: false,
                submenu: {
                    directory: {
                        separator_before: false,
                        separator_after: false,
                        label: _t("Directory"),
                        icon: "fa fa-folder",
                        action: function(data) {
                            var inst = $.jstree.reference(data.reference);
                            var obj = inst.get_node(data.reference);
                            create(inst.settings.widget, "muk_dms.directory", obj.data.odoo_id);
                        }
                    },
                    file : {
                        separator_before: false,
                        separator_after: false,
                        label: _t("File"),
                        icon: "fa fa-file",
                        action: function(data) {
                            var inst = $.jstree.reference(data.reference);
                            var obj = inst.get_node(data.reference);
                            create(inst.settings.widget, "muk_dms.file", obj.data.odoo_id);
                        }
                    },
                }
            };
        }
        return items;
    }

    DocumentTreeView.include({
        load_view: function() {
            var self = this;
            $.when(self.load_directories(self)).done(function (directories, directory_ids) {
                $.when(self.load_files(self, directory_ids)).done(function (files) {
                    var data = directories.concat(files);
                    self.$el.find('.oe_document_tree').jstree({
                        'widget': self,
                        'core': {
                            'animation': 0,
                            'multiple': false,
                            'check_callback': true,
                            'themes': { "stripes": true },
                            'data': data
                        },
                        'plugins': [
                            "contextmenu", "search", "sort", "state", "wholerow", "types"
                        ],
                        'search': {
                            'case_sensitive': false,
                            'show_only_matches': true,
                            'show_only_matches_children' : true,
                        },
                        'sort' : function (a, b) {
                            if (this.get_text(a) === "Autres") {
                                return 1;
                            }
                            else if (this.get_text(b) === "Autres") {
                                return -1;
                            }
                            return this.get_text(a).toLowerCase() > this.get_text(b).toLowerCase() ? 1 : -1;
                        },
                        'contextmenu': {
                            items: context_menu_items
                        },
                    }).on('open_node.jstree', function (e, data) {
                        data.instance.set_icon(data.node, "fa fa-folder-open-o");
                    }).on('close_node.jstree', function (e, data) {
                        data.instance.set_icon(data.node, "fa fa-folder-o");
                    }).bind('loaded.jstree', function(e, data) {
                        self.show_preview();
                    }).on('changed.jstree', function (e, data) {
                        if(data.node) {
                            self.selected_node = data.node;
                            self.$el.find('button.open').prop('disabled', !self.selected_node.data.perm_read);
                            self.$el.find('button.edit').prop('disabled', !self.selected_node.data.perm_write);
                            self.$el.find('button.create_file').prop('disabled',
                                    self.selected_node.data.odoo_model != "muk_dms.directory" || !self.selected_node.data.perm_create);
                            self.$el.find('button.create_directory').prop('disabled',
                                    self.selected_node.data.odoo_model != "muk_dms.directory" || !self.selected_node.data.perm_create);
                            $("#menuContinenti").prop('disabled', function (_, val) { return ! val; });
                            if(self.show_preview_active && data.node.data.odoo_model == "muk_dms.file") {
                                PreviewHelper.createFilePreviewContent(data.node.data.odoo_id).then(function($content) {
                                    self.$el.find('.oe_document_preview').html($content);
                                });
                            }
                        }
                    });
                    var timeout = false;
                    self.$el.find('#tree_search').keyup(function() {
                        if(timeout) {
                            clearTimeout(timeout);
                        }
                        timeout = setTimeout(function() {
                            var v = self.$el.find('#tree_search').val();
                            self.$('.oe_document_tree').jstree(true).search(v);
                        }, 250);
                   });
                });
            });
        },
    });
});
