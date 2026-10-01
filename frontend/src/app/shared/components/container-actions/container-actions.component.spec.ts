import { signal, WritableSignal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideTranslateService } from '@ngx-translate/core';
import { EJobStatus, IHostState } from '@shared/interfaces/jobs.interface';
import { EContainerStatus } from 'src/app/features/containers/containers.interface';
import { IContainerEntity } from 'src/app/features/containers/containers.store';
import { IHostEntity } from 'src/app/features/hosts/hosts.store';
import {
  ESettingKey,
  ISetting,
} from 'src/app/features/settings/settings.interface';
import { SettingsStore } from 'src/app/features/settings/settings.store';
import { ContainerActionsComponent } from './container-actions.component';

const container = (partial: Partial<IContainerEntity> = {}): IContainerEntity =>
  ({
    name: 'web',
    status: EContainerStatus.running,
    protected: false,
    update_available: true,
    loading: null,
    ...partial,
  }) as IContainerEntity;

const host = (partial: Partial<IHostEntity> = {}): IHostEntity =>
  ({
    id: 1,
    name: 'local',
    loading: null,
    jobState: null,
    ...partial,
  }) as IHostEntity;

describe('ContainerActionsComponent', () => {
  let fixture: ComponentFixture<ContainerActionsComponent>;
  let component: ContainerActionsComponent;
  let settings: WritableSignal<Record<string, ISetting>>;

  beforeEach(async () => {
    settings = signal({});

    await TestBed.configureTestingModule({
      imports: [ContainerActionsComponent],
      providers: [
        provideTranslateService(),
        {
          provide: SettingsStore,
          useValue: { entityMap: settings },
        },
      ],
    })
      .overrideComponent(ContainerActionsComponent, {
        set: { template: '' },
      })
      .compileComponents();

    fixture = TestBed.createComponent(ContainerActionsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('item', container());
    fixture.componentRef.setInput('host', host());
  });

  describe('showControlButtons', () => {
    it('hides them by default', () => {
      expect(component['showControlButtons']()).toBe(false);
    });

    it('shows them when control is enabled', () => {
      fixture.componentRef.setInput('withControl', true);

      expect(component['showControlButtons']()).toBe(true);
    });

    it('hides them for a protected container', () => {
      fixture.componentRef.setInput('withControl', true);
      fixture.componentRef.setInput('item', container({ protected: true }));

      expect(component['showControlButtons']()).toBe(false);
    });
  });

  describe('update', () => {
    it('allows a running container that has an update', () => {
      expect(component['cantUpdate']()).toBe(false);
      expect(component['showUpdateTooltip']()).toBe(false);
    });

    it('blocks a stopped container and explains why', () => {
      fixture.componentRef.setInput(
        'item',
        container({ status: EContainerStatus.exited }),
      );

      expect(component['cantUpdate']()).toBe(true);
      expect(component['showUpdateTooltip']()).toBe(true);
    });

    it('allows a stopped container when stopped updates are allowed', () => {
      settings.set({
        [ESettingKey.UPDATE_ONLY_RUNNING]: {
          key: ESettingKey.UPDATE_ONLY_RUNNING,
          value: false,
        } as ISetting,
      });
      fixture.componentRef.setInput(
        'item',
        container({ status: EContainerStatus.exited }),
      );

      expect(component['cantUpdate']()).toBe(false);
      expect(component['showUpdateTooltip']()).toBe(false);
    });

    it('blocks a protected container and explains why', () => {
      fixture.componentRef.setInput('item', container({ protected: true }));

      expect(component['cantUpdate']()).toBe(true);
      expect(component['showUpdateTooltip']()).toBe(true);
    });

    it('blocks an update without a tooltip when nothing is available', () => {
      fixture.componentRef.setInput(
        'item',
        container({ update_available: false }),
      );

      expect(component['cantUpdate']()).toBe(true);
      expect(component['showUpdateTooltip']()).toBe(false);
    });
  });

  describe('commands', () => {
    it('stops a running container', () => {
      expect(component['canStart']()).toBe(false);
      expect(component['canStop']()).toBe(true);
    });

    it('starts an exited container', () => {
      fixture.componentRef.setInput(
        'item',
        container({ status: EContainerStatus.exited }),
      );

      expect(component['canStart']()).toBe(true);
      expect(component['canStop']()).toBe(false);
    });
  });

  describe('hostActionLoading', () => {
    it('is idle by default', () => {
      expect(component['hostActionLoading']()).toBe(false);
    });

    it('is busy while the host is pruning', () => {
      fixture.componentRef.setInput('host', host({ loading: 'prune' }));

      expect(component['hostActionLoading']()).toBe(true);
    });

    it('is busy while a job includes this container', () => {
      const jobState: IHostState = {
        status: EJobStatus.CHECKING,
        current: { names: ['web'] },
      };
      fixture.componentRef.setInput('host', host({ jobState }));

      expect(component['hostActionLoading']()).toBe(true);
    });

    it('stays idle while a job runs for another container', () => {
      fixture.componentRef.setInput(
        'host',
        host({
          jobState: {
            status: EJobStatus.CHECKING,
            current: { names: ['other'] },
            queued: [],
          },
        }),
      );

      expect(component['hostActionLoading']()).toBe(false);
    });
  });
});
