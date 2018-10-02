/*
 *  EzTech Software & Consultancy Inc. (c) 2017
 */
odoo.define('wc.security', function(require) {
"use strict";

var core = require('web.core');
var Sidebar = require('web.Sidebar');
var MailComposer = require('mail.composer')
var Dialog = require('web.Dialog');
var FieldBinaryFile = core.form_widget_registry.get('binary');

var _t = core._t;

function attachment_check(e) {
  console.log("attachment:",e);
  var filetype = e.target.files["0"].type;

  var whitelist = [
    'application/pdf',
    'text/plain',
    'text/html',
    'text/csv',
    'image/gif',
    'image/png',
    'image/jpeg',
    'image/bmp',
    'image/webp',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.openxmlformats-officedocument.presentationml.template',
    'application/vnd.openxmlformats-officedocument.presentationml.slideshow'
  ];

  var allowed = [
     "pdf","text","csv","images","word","excel"
  ]

  console.log("filetype:",filetype);
  //this.do_warn(_t("Attach test:"),"filetype="+filetype);
  if (whitelist.indexOf(filetype)<0) {
    Dialog.alert(self,
      "Only the following file types can be attached:\n" + (allowed.join(", ")),
      {title:_t("Attachment Error!")}
    );
    return 0;
  } else {
    return 1;
  }
}

//Attach button at top-center
Sidebar.include({
  on_attachment_changed: function(e) {
    var self = this;
    if (attachment_check(e)) {
      self._super(e);
    }
  }
});

//Message file attachment
MailComposer.BasicComposer.include({
  on_attachment_change: function(e) {
    var self = this;
    if (attachment_check(e)) {
      self._super(e);
    } else {
      this.$('input.o_form_input_file').val("");
    }
  }
});

//Attachment of binary file field type
FieldBinaryFile.include({
  on_file_change: function(e) {
    var self = this;
    if (attachment_check(e)) {
      self._super(e);
    } else {
      this.$('.o_form_input_file').val("");
    }
  }
});

});
