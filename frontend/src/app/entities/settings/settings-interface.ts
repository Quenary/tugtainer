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
  TIMEZONE = 'TIMEZONE',
  NOTIFICATION_URLS = 'NOTIFICATION_URLS',
  NOTIFICATION_TITLE_TEMPLATE = 'NOTIFICATION_TITLE_TEMPLATE',
  NOTIFICATION_BODY_TEMPLATE = 'NOTIFICATION_BODY_TEMPLATE',
}
export interface ITestNotificationRequestBody {
  title_template: string;
  body_template: string;
  urls: string;
}
export const ESettingSortIndex: { [K in ESettingKey]: number } = {
  [ESettingKey.CRONTAB_EXPR]: 0,
  [ESettingKey.TIMEZONE]: 1,
  [ESettingKey.NOTIFICATION_URLS]: 2,
  [ESettingKey.NOTIFICATION_TITLE_TEMPLATE]: 3,
  [ESettingKey.NOTIFICATION_BODY_TEMPLATE]: 4,
};
