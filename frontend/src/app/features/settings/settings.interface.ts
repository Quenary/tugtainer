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
  CHECK_CRONTAB_EXPR = 'CHECK_CRONTAB_EXPR',
  UPDATE_CRONTAB_EXPR = 'UPDATE_CRONTAB_EXPR',
  REGISTRY_REQ_DELAY = 'REGISTRY_REQ_DELAY',
  PULL_BEFORE_CHECK = 'PULL_BEFORE_CHECK',
  TIMEZONE = 'TIMEZONE',
  NOTIFICATION_URLS = 'NOTIFICATION_URLS',
  NOTIFICATION_TITLE_TEMPLATE = 'NOTIFICATION_TITLE_TEMPLATE',
  NOTIFICATION_BODY_TEMPLATE = 'NOTIFICATION_BODY_TEMPLATE',
  UPDATE_ONLY_RUNNING = 'UPDATE_ONLY_RUNNING',
  INSECURE_REGISTRIES = 'INSECURE_REGISTRIES',
  DELAY_UPDATE_FOR = 'DELAY_UPDATE_FOR',
}
export interface ITestNotificationRequestBody {
  title_template: string;
  body_template: string;
  urls: string;
}
export const settingKeysOrder: ESettingKey[] = [
  ESettingKey.CHECK_CRONTAB_EXPR,
  ESettingKey.UPDATE_CRONTAB_EXPR,
  ESettingKey.TIMEZONE,
  ESettingKey.REGISTRY_REQ_DELAY,
  ESettingKey.PULL_BEFORE_CHECK,
  ESettingKey.INSECURE_REGISTRIES,
  ESettingKey.UPDATE_ONLY_RUNNING,
  ESettingKey.DELAY_UPDATE_FOR,
  ESettingKey.NOTIFICATION_URLS,
  ESettingKey.NOTIFICATION_TITLE_TEMPLATE,
  ESettingKey.NOTIFICATION_BODY_TEMPLATE,
];
