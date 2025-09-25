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
}
