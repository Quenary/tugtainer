export enum ESettingValueType {
  BOOL = 'bool',
  FLOAT = 'float',
  INT = 'int',
  STR = 'str',
}
export interface ISetting {
  key: ESettingKey;
  value: boolean | number | string;
  value_type: ESettingValueType;
  modified_at: string;
}
export interface ISettingUpdate {
  key: string;
  value: boolean | number | string;
}
export enum ESettingKey {
  CRONTAB_EXPR = 'CRONTAB_EXPR',
  NOTIFICATION_URL = 'NOTIFICATION_URL',
  TIMEZONE = 'TIMEZONE',
  DOCKER_TIMEOUT = 'DOCKER_TIMEOUT',
  
  // OIDC Settings
  OIDC_ENABLED = 'OIDC_ENABLED',
  OIDC_WELL_KNOWN_URL = 'OIDC_WELL_KNOWN_URL',
  OIDC_CLIENT_ID = 'OIDC_CLIENT_ID',
  OIDC_CLIENT_SECRET = 'OIDC_CLIENT_SECRET',
  OIDC_REDIRECT_URI = 'OIDC_REDIRECT_URI',
  OIDC_SCOPES = 'OIDC_SCOPES',
}
