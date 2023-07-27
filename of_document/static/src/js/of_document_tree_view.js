odoo.define('of_document.documents', function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var dms_utils = require('muk_dms.utils');
    var framework = require('web.framework');
    var Model = require("web.Model");
    var _t = core._t;

    var Directories = new Model('muk_dms.directory', session.user_context);
    var Files = new Model('muk_dms.file', session.user_context);

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

        init: function(parent, context) {
            this._super(parent, context);
            this.events = _.extend(this.events, {
                "click .go_back_contacts": "go_back_contacts",
                "click .go_back_customer": "go_back_customer",
            });
            this.name = 'Documents';
            this.partner_filter_folders = null;
            this.partner_filter_files = null;
            this.partner_name = null;
            this.parent_directory_id = null;
            if (context.context.partner_id) {
                this.partner_id = context.context.partner_id;
                this.partner_name = context.context.partner_name;
            }
            if (context.context.parent_directory_id) {
                this.parent_directory_id = context.context.parent_directory_id;
            }
            if (this.partner_id && this.parent_directory_id) {
                this.partner_filter_folders = ['|', ['of_partner_id', '=', this.partner_id], ['parent_directory', 'child_of', this.parent_directory_id]];
                this.partner_filter_files = ['|', ['of_partner_id', '=', this.partner_id], ['directory', 'child_of', this.parent_directory_id]];
            } else if (this.partner_id) {
                this.partner_filter_folders = [['of_partner_id', '=', this.partner_id]];
                this.partner_filter_files = [['of_partner_id', '=', this.partner_id]];
            } else if (this.parent_directory_id) {
                this.partner_filter_folders = [['parent_directory', 'child_of', this.parent_directory_id]];
                this.partner_filter_files = [['directory', 'child_of', this.parent_directory_id]];
            }

            this.splitter = false;
        },

        go_back_customer: function() {
            history.back();
        },

        go_back_contacts: function() {
            var self = this;
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'res.partner',
                name: 'Contacts',
                views: [
                    [false, 'list'],
                    [false, 'kanban'],
                    [false, 'form'],
                ],
                target: 'current',
                context: {},
            }, {clear_breadcrumbs: true});
        },

        load_directories: function(self) {
            var self = this;
            var directories_query = $.Deferred();
            Directories.query(['name', 'parent_directory', 'perm_read', 'perm_create',
                    'perm_write', 'perm_unlink']).filter(self.partner_filter_folders).all().then(function(directories) {
                var data = [];
                var directory_ids = _.map(directories, function(directory, index) {
                    return directory.id;
                });
                _.each(directories, function(value, key, list) {
                    data.push({
                        id: "directory_" + value.id,
                        parent: (value.parent_directory &&
                                $.inArray(value.parent_directory[0], directory_ids) !== -1 ?
                                        "directory_" + value.parent_directory[0] : "#"),
                        text: value.name,
                        icon: "fa fa-folder-o",
                        type: "directory",
                        data: {
                            container: false,
                            odoo_id: value.id,
                            odoo_parent_directory: value.parent_directory[0],
                            odoo_model: "muk_dms.directory",
                            perm_read: value.perm_read,
                            perm_create: value.perm_create,
                            perm_write: value.perm_write,
                            perm_unlink: value.perm_unlink,
                        }
                    });
                });
                directories_query.resolve(data, directory_ids);
            });
            return directories_query;
        },

        load_files: function(self, directory_ids) {
            var self = this;
            var files_query = $.Deferred();
            Files.query(['name', 'mimetype', 'extension', 'directory',
                         'size', 'perm_read','perm_create', 'perm_write',
                         'perm_unlink']).filter(self.partner_filter_files).all().then(function(files) {
                var data = [];
                _.each(files, function(value, key, list) {
                    if(!($.inArray(value.directory[0], directory_ids) !== -1)) {
                        directory_ids.push(value.directory[0]);
                        data.push(self.add_container_directory(self, value.directory[0], value.directory[1]));
                    }
                    data.push({
                        id: "file," + value.id,
                        parent: "directory_" + value.directory[0],
                        text: value.name,
                        icon: dms_utils.mimetype2fa(value.mimetype, {prefix: "fa fa-"}),
                        type: "file",
                        data: {
                            odoo_id: value.id,
                            odoo_parent_directory: value.directory[0],
                            odoo_model: "muk_dms.file",
                            filename: value.name,
                            file_size: value.file_size,
                            preview_link: value.link_preview,
                            download_link: value.link_download,
                            file_extension: value.file_extension,
                            mime_type: value.mime_type,
                            perm_read: value.perm_read,
                            perm_create: value.perm_create,
                            perm_write: value.perm_write,
                            perm_unlink: value.perm_unlink,
                        }
                    });
                });
                files_query.resolve(data);
            });
            return files_query;
        },

        load_view: function() {
            var self = this;
            $.when(self.load_directories(self)).done(function (directories, directory_ids) {
                $.when(self.load_files(self, directory_ids)).done(function (files) {
                    if(self.partner_id) {
                        $('.go_back_customer').append(self.partner_name);
                        $('.document_breadcrumb').show();
                    }
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
