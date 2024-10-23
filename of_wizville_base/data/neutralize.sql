-- disable wizville config
DELETE FROM ir_config_parameter
WHERE key IN ('wizville_sftp_host', 'wizville_sftp_port', 'wizville_sftp_user', 'wizville_sftp_password', 'wizville_sftp_deposit_directory', 'wizville_sftp_pickup_directory')
