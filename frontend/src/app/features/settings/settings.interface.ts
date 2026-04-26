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
}
export interface ITestNotificationRequestBody {
  title_template: string;
  body_template: string;
  urls: string;
}
export const ESettingSortIndex: Record<ESettingKey, number> = {
  [ESettingKey.CHECK_CRONTAB_EXPR]: 0,
  [ESettingKey.UPDATE_CRONTAB_EXPR]: 1,
  [ESettingKey.TIMEZONE]: 2,
  [ESettingKey.REGISTRY_REQ_DELAY]: 3,
  [ESettingKey.PULL_BEFORE_CHECK]: 4,
  [ESettingKey.INSECURE_REGISTRIES]: 5,
  [ESettingKey.UPDATE_ONLY_RUNNING]: 6,
  [ESettingKey.NOTIFICATION_URLS]: 7,
  [ESettingKey.NOTIFICATION_TITLE_TEMPLATE]: 8,
  [ESettingKey.NOTIFICATION_BODY_TEMPLATE]: 9,
};
