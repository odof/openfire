-- disable wizville config
DELETE FROM ir_config_parameter WHERE key IN ('of.wizville.base.wizville_sftp_host', 'of.wizville.base.wizville_sftp_port', 'of.wizville.base.wizville_sftp_user', 'of.wizville.base.wizville_sftp_password');
