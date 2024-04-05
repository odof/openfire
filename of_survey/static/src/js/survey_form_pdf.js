odoo.define('of_survey.form_pdf', function(require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.OFSurveyFormPDFWidget = publicWidget.Widget.extend({
        template: "of_survey.survey_form_pdf_template",

        events: {
            'change .annotationLayer': 'onChangeAnnotationLayer',
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.question_id = options.question_id;
            this.annotations = false;
        },

        start: async function() {
            var self = this;
            this.container = $(this.$el);
            const eventBus = new window.pdfjsViewer.EventBus();
            const pdfLinkService = new window.pdfjsViewer.PDFLinkService({
              eventBus,
            });
            let data = $(this.container).find('.pdfViewer').attr('data');
            this.pdf = await window.pdfjsLib.getDocument({url: data}).promise;
            var pageNumber = 1;
            this.page = await this.pdf.getPage(pageNumber)
            var scale = 1;
            var viewport = this.page.getViewport({ scale: scale });
            var canvas_id = $(this.container).find("canvas");
            var layer_id = $(this.container).find(".annotationLayer");

            // Prepare canvas using PDF page dimensions
            var canvas = $(canvas_id)[0];
            var layer = $(layer_id)[0];

            var context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            canvas.style.height = `${viewport.height}px`;
            canvas.style.width = `${viewport.width}px`;

            // Render PDF page into canvas context
            var renderContext = {
                canvasContext: context,
                viewport: viewport,
            };
            await this.page.render(renderContext);
            this.annotations = await this.page.getAnnotations();
            await window.pdfjsLib.AnnotationLayer.render({
                viewport: viewport.clone({
                    dontFlip: true
                  }),
                div: layer,
                annotations: self.annotations,
                page: this.page,
                renderForms: true,
                linkService: pdfLinkService,
            });
            // on positionne le layer sur le pdf
            $(layer).css({ top: $(canvas).position().top, left: $(canvas).position().left});

        },

        onChangeAnnotationLayer: function(event){
            let name = $(event.target).attr('name');
            let value = $(event.target).val();
            // on va chercher dans les annotations l'id du champs
            let annotation = this.annotations.find((annotation) => annotation.fieldName == name);
            this.pdf.annotationStorage.setValue(annotation.id,{ 'value' : value });
        }
    });
});
