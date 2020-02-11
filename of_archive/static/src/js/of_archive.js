odoo.define('of_archive.archive_pdf_viewer', function (require) {
"use strict";

var core = require('web.core');
var utils = require('web.utils');
var FieldBinaryFile = core.form_widget_registry.get('binary');

var FieldOFPdfViewer = FieldBinaryFile.extend({
    template: 'FieldOFPdfViewer',
    init: function(){
        this._super.apply(this, arguments);
        this.PDFViewerApplication = false;
    },
    start: function(){
        this._super.apply(this, arguments);
        this._ic_field_manager.on('view_content_has_changed', this, function() {
            this.render_value();
         });
    },
    get_uri: function(){
        var query_obj = {
            model: this.view.dataset.model,
            field: this.name,
            id: this.view.datarecord.id
        };
        var query_string = $.param(query_obj);
        var url = encodeURIComponent('/web/image?' + query_string);
        var viewer_url = '/web/static/lib/pdfjs/web/viewer.html?file=';
        return viewer_url + url;
    },
    on_file_change: function(ev) {
        this._super.apply(this, arguments);
        if(this.PDFViewerApplication){
            var files = ev.target.files;
            if (!files || files.length === 0) {
              return;
            }
            var file = files[0];
            // TOCheck: is there requirement to fallback on FileReader if browser don't support URL
            this.PDFViewerApplication.open(URL.createObjectURL(file), 0);
        }
    },
    render_value: function() {
        var $pdf_viewer = this.$('.of_form_pdf_controls').children().add(this.$('.of_pdfview_iframe')),
            $select_upload_el = this.$('.o_select_file_button').first(),
            $iFrame = this.$('.of_pdfview_iframe'),
            value = this.get('value'),
            self = this;

        var bin_size = utils.is_bin_size(value);
        $iFrame.on('load', function(){
            self.PDFViewerApplication = this.contentWindow.window.PDFViewerApplication;
            self.disable_buttons(this);
        });
        if (this.get("effective_readonly")) {
            if (value) {
                this.$el.off('click'); // off click event(on_save_as) of FieldBinaryFile
                $iFrame.attr('src', this.get_uri());
            }
        } else {
            if (value) {
                $pdf_viewer.removeClass('o_hidden');
                $select_upload_el.addClass('o_hidden');
                if(bin_size){
                    $iFrame.attr('src', this.get_uri());
                }
            } else {
                $pdf_viewer.addClass('o_hidden');
                $select_upload_el.removeClass('o_hidden');
            }
        }
    },
    disable_buttons: function(iframe){
        if (this.get("effective_readonly")){
            $(iframe).contents().find('button#download').hide();
        }
        $(iframe).contents().find('button#openFile').hide();
    }

});

core.form_widget_registry.add('of_pdf_viewer', FieldOFPdfViewer);

});
