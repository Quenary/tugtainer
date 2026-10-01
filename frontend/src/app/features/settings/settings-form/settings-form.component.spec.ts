import { signal, WritableSignal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideTranslateService } from '@ngx-translate/core';
import {
  ESettingKey,
  ESettingValueType,
  ISetting,
} from '../settings.interface';
import { SettingsStore } from '../settings.store';
import { SettingsFormComponent } from './settings-form.component';

const setting = (
  key: ESettingKey,
  value: ISetting['value'],
  valueType = ESettingValueType.STR,
): ISetting => ({
  key,
  value,
  value_type: valueType,
  modified_at: '2026-01-01T00:00:00Z',
});

describe('SettingsFormComponent', () => {
  let fixture: ComponentFixture<SettingsFormComponent>;
  let component: SettingsFormComponent;
  let entities: WritableSignal<ISetting[]>;
  let timezones: WritableSignal<string[]>;
  let change: ReturnType<typeof vi.fn>;
  let testNotification: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    entities = signal<ISetting[]>([]);
    timezones = signal<string[]>([]);
    change = vi.fn();
    testNotification = vi.fn();

    await TestBed.configureTestingModule({
      imports: [SettingsFormComponent],
      providers: [
        provideTranslateService(),
        {
          provide: SettingsStore,
          useValue: {
            entities,
            timezones,
            loading: signal(false),
            change,
            testNotification,
          },
        },
      ],
    })
      .overrideComponent(SettingsFormComponent, {
        set: { template: '' },
      })
      .compileComponents();

    fixture = TestBed.createComponent(SettingsFormComponent);
    component = fixture.componentInstance;
  });

  const syncForm = (): void => {
    TestBed.flushEffects();
  };

  const control = (key: ESettingKey) =>
    component['formArray'].controls.find((item) => item.value.key === key)!;

  it('builds the form in the settings display order', () => {
    entities.set([
      setting(ESettingKey.TIMEZONE, 'UTC'),
      setting(ESettingKey.CHECK_CRONTAB_EXPR, '0 * * * *'),
      setting(ESettingKey.UPDATE_ONLY_RUNNING, true, ESettingValueType.BOOL),
    ]);
    syncForm();

    expect(
      component['formArray'].controls.map((item) => item.value.key),
    ).toEqual([
      ESettingKey.CHECK_CRONTAB_EXPR,
      ESettingKey.TIMEZONE,
      ESettingKey.UPDATE_ONLY_RUNNING,
    ]);
  });

  describe('cron validator', () => {
    beforeEach(() => {
      entities.set([setting(ESettingKey.CHECK_CRONTAB_EXPR, '0 * * * *')]);
      syncForm();
    });

    it('requires a value', () => {
      const cron = control(ESettingKey.CHECK_CRONTAB_EXPR).controls.value;
      cron.setValue('');

      expect(cron.hasError('required')).toBe(true);
    });

    it('rejects an invalid expression', () => {
      const cron = control(ESettingKey.CHECK_CRONTAB_EXPR).controls.value;
      cron.setValue('not a cron');

      expect(cron.hasError('cronValidator')).toBe(true);
    });

    it('accepts a valid expression', () => {
      const cron = control(ESettingKey.CHECK_CRONTAB_EXPR).controls.value;
      cron.setValue('*/15 * * * *');

      expect(cron.valid).toBe(true);
    });
  });

  describe('timezone validator', () => {
    beforeEach(() => {
      entities.set([setting(ESettingKey.TIMEZONE, 'UTC')]);
      syncForm();
    });

    it('accepts any value before the list is loaded', () => {
      const timezone = control(ESettingKey.TIMEZONE).controls.value;
      timezone.setValue('Europe/Berlin');

      expect(timezone.valid).toBe(true);
    });

    it('rejects a value missing from the loaded list', () => {
      timezones.set(['UTC', 'Europe/Moscow']);
      const timezone = control(ESettingKey.TIMEZONE).controls.value;
      timezone.setValue('Europe/Berlin');
      timezone.updateValueAndValidity();

      expect(timezone.hasError('timezoneValidator')).toBe(true);
    });

    it('accepts a value from the loaded list', () => {
      timezones.set(['UTC', 'Europe/Moscow']);
      const timezone = control(ESettingKey.TIMEZONE).controls.value;
      timezone.setValue('Europe/Moscow');

      expect(timezone.valid).toBe(true);
    });
  });

  describe('displayedTimezones', () => {
    beforeEach(() => {
      timezones.set(['UTC', 'Europe/Moscow', 'America/New_York']);
    });

    it('returns the full list without a query', () => {
      expect(component['displayedTimezones']()).toEqual([
        'UTC',
        'Europe/Moscow',
        'America/New_York',
      ]);
    });

    it('filters by a case-insensitive query', () => {
      component['timezonesAutocompleteEvent'].set({
        query: 'europe',
        originalEvent: new Event('input'),
      });

      expect(component['displayedTimezones']()).toEqual(['Europe/Moscow']);
    });
  });

  describe('submit', () => {
    beforeEach(() => {
      entities.set([
        setting(ESettingKey.CHECK_CRONTAB_EXPR, '0 * * * *'),
        setting(ESettingKey.TIMEZONE, 'UTC'),
      ]);
      timezones.set(['UTC', 'Europe/Moscow']);
      syncForm();
    });

    it('does nothing while the form is invalid', () => {
      const cron = control(ESettingKey.CHECK_CRONTAB_EXPR);
      cron.controls.value.setValue('not a cron');
      cron.markAsDirty();

      component['submit']();

      expect(change).not.toHaveBeenCalled();
    });

    it('saves only dirty settings', () => {
      const cron = control(ESettingKey.CHECK_CRONTAB_EXPR);
      cron.controls.value.setValue('0 3 * * *');
      cron.markAsDirty();
      const timezone = control(ESettingKey.TIMEZONE);
      timezone.controls.value.setValue('Europe/Moscow');
      timezone.markAsDirty();

      component['submit']();

      expect(change).toHaveBeenCalledWith({
        entities: [
          { key: ESettingKey.CHECK_CRONTAB_EXPR, value: '0 3 * * *' },
          { key: ESettingKey.TIMEZONE, value: 'Europe/Moscow' },
        ],
      });
    });
  });

  it('sends the notification templates currently in the form', () => {
    entities.set([
      setting(ESettingKey.NOTIFICATION_TITLE_TEMPLATE, 'title'),
      setting(ESettingKey.NOTIFICATION_BODY_TEMPLATE, 'body'),
      setting(ESettingKey.NOTIFICATION_URLS, 'https://example.test'),
    ]);
    syncForm();

    control(ESettingKey.NOTIFICATION_TITLE_TEMPLATE).controls.value.setValue(
      'edited title',
    );
    component['onTestNotification']();

    expect(testNotification).toHaveBeenCalledWith({
      title_template: 'edited title',
      body_template: 'body',
      urls: 'https://example.test',
    });
  });
});
