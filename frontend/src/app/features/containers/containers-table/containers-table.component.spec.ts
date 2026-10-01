import { signal, WritableSignal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideTranslateService } from '@ngx-translate/core';
import { EContainerStatus } from '../containers.interface';
import { ContainersStore, IContainerEntity } from '../containers.store';
import { ESettingKey, ISetting } from '../../settings/settings.interface';
import { SettingsStore } from '../../settings/settings.store';
import { ContainersTableComponent } from './containers-table.component';

const onlyAvailableStorageKey = 'tugtainer-containers-only-available';
const statusesStorageKey = 'tugtainer-containers-statuses';

const container = (
  partial: Partial<IContainerEntity> & Pick<IContainerEntity, 'name'>,
): IContainerEntity =>
  ({
    status: EContainerStatus.running,
    protected: false,
    update_available: false,
    ...partial,
  }) as IContainerEntity;

describe('ContainersTableComponent', () => {
  let fixture: ComponentFixture<ContainersTableComponent>;
  let component: ContainersTableComponent;
  let entities: WritableSignal<IContainerEntity[]>;
  let settings: WritableSignal<Record<string, ISetting>>;
  let containersStore: {
    entities: WritableSignal<IContainerEntity[]>;
    loadList: ReturnType<typeof vi.fn>;
    checkContainers: ReturnType<typeof vi.fn>;
    updateContainers: ReturnType<typeof vi.fn>;
    controlContainers: ReturnType<typeof vi.fn>;
  };

  const runningUpdate = container({
    name: 'web',
    update_available: true,
  });
  const stoppedUpdate = container({
    name: 'db',
    status: EContainerStatus.exited,
    update_available: true,
  });
  const protectedUpdate = container({
    name: 'agent',
    update_available: true,
    protected: true,
  });
  const current = container({
    name: 'cache',
    status: EContainerStatus.paused,
  });

  beforeEach(async () => {
    localStorage.removeItem(onlyAvailableStorageKey);
    localStorage.removeItem(statusesStorageKey);

    entities = signal([runningUpdate, stoppedUpdate, protectedUpdate, current]);
    settings = signal({});
    containersStore = {
      entities,
      loadList: vi.fn(),
      checkContainers: vi.fn(),
      updateContainers: vi.fn(),
      controlContainers: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [ContainersTableComponent],
      providers: [
        provideTranslateService(),
        { provide: ContainersStore, useValue: containersStore },
        {
          provide: SettingsStore,
          useValue: { entityMap: settings },
        },
      ],
    })
      .overrideComponent(ContainersTableComponent, {
        set: { template: '' },
      })
      .compileComponents();

    fixture = TestBed.createComponent(ContainersTableComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    localStorage.removeItem(onlyAvailableStorageKey);
    localStorage.removeItem(statusesStorageKey);
  });

  it('loads the list on init', () => {
    expect(containersStore.loadList).toHaveBeenCalledTimes(1);
  });

  describe('filteredList', () => {
    it('includes every container', () => {
      expect(component['filteredList']().map((item) => item.name)).toEqual([
        'web',
        'db',
        'agent',
        'cache',
      ]);
    });

    it('keeps containers that have an update', () => {
      component['onlyAvailable'].set(true);

      expect(component['filteredList']().map((item) => item.name)).toEqual([
        'web',
        'db',
        'agent',
      ]);
    });

    it('keeps the selected statuses', () => {
      component['statuses'].set([
        EContainerStatus.exited,
        EContainerStatus.paused,
      ]);

      expect(component['filteredList']().map((item) => item.name)).toEqual([
        'db',
        'cache',
      ]);
    });

    it('ignores an empty status selection', () => {
      component['statuses'].set([]);

      expect(component['filteredList']()).toHaveLength(4);
    });

    it('combines both filters', () => {
      component['onlyAvailable'].set(true);
      component['statuses'].set([EContainerStatus.exited]);

      expect(component['filteredList']().map((item) => item.name)).toEqual([
        'db',
      ]);
    });
  });

  describe('updatableSelected', () => {
    it('keeps unprotected running containers', () => {
      component['selected'].set([
        runningUpdate,
        stoppedUpdate,
        protectedUpdate,
        current,
      ]);

      expect(component['updatableSelected']().map((item) => item.name)).toEqual(
        ['web'],
      );
    });

    it('includes stopped containers when stopped updates are allowed', () => {
      settings.set({
        [ESettingKey.UPDATE_ONLY_RUNNING]: {
          key: ESettingKey.UPDATE_ONLY_RUNNING,
          value: false,
          value_type: 'bool',
          modified_at: '',
        } as ISetting,
      });
      component['selected'].set([
        runningUpdate,
        stoppedUpdate,
        protectedUpdate,
      ]);

      expect(component['updatableSelected']().map((item) => item.name)).toEqual(
        ['web', 'db'],
      );
    });
  });

  describe('onCheckSelected', () => {
    it('does nothing when the selection is empty', () => {
      component['onCheckSelected']();

      expect(containersStore.checkContainers).not.toHaveBeenCalled();
    });

    it('checks every selected container and clears the selection', () => {
      component['selected'].set([runningUpdate, current]);

      component['onCheckSelected']();

      expect(containersStore.checkContainers).toHaveBeenCalledWith({
        names: ['web', 'cache'],
      });
      expect(component['selected']()).toEqual([]);
    });
  });

  describe('onUpdateSelected', () => {
    it('does nothing when nothing can be updated', () => {
      component['selected'].set([stoppedUpdate, protectedUpdate]);

      component['onUpdateSelected']();

      expect(containersStore.updateContainers).not.toHaveBeenCalled();
      expect(component['selected']()).toEqual([stoppedUpdate, protectedUpdate]);
    });

    it('updates the updatable selection and clears it', () => {
      component['selected'].set([
        runningUpdate,
        stoppedUpdate,
        protectedUpdate,
      ]);

      component['onUpdateSelected']();

      expect(containersStore.updateContainers).toHaveBeenCalledWith({
        names: ['web'],
      });
      expect(component['selected']()).toEqual([]);
    });
  });

  describe('onBulkCommand', () => {
    it('does nothing without containers', () => {
      component['selected'].set([runningUpdate]);

      component['onBulkCommand']({ command: 'stop', containers: [] });

      expect(containersStore.controlContainers).not.toHaveBeenCalled();
      expect(component['selected']()).toEqual([runningUpdate]);
    });

    it('sends the command and clears the selection', () => {
      component['selected'].set([runningUpdate, stoppedUpdate]);

      component['onBulkCommand']({
        command: 'restart',
        containers: [runningUpdate],
      });

      expect(containersStore.controlContainers).toHaveBeenCalledWith({
        names: ['web'],
        command: 'restart',
      });
      expect(component['selected']()).toEqual([]);
    });
  });

  describe('stored filters', () => {
    it('restores the available and status filters', () => {
      localStorage.setItemJson(onlyAvailableStorageKey, true);
      localStorage.setItemJson(statusesStorageKey, [EContainerStatus.running]);
      fixture = TestBed.createComponent(ContainersTableComponent);
      component = fixture.componentInstance;

      expect(component['onlyAvailable']()).toBe(true);
      expect(component['statuses']()).toEqual([EContainerStatus.running]);
    });

    it('persists filter changes', () => {
      component['onlyAvailable'].set(false);
      component['statuses'].set([EContainerStatus.paused]);
      TestBed.flushEffects();

      expect(localStorage.getItemJson(onlyAvailableStorageKey)).toBe(false);
      expect(localStorage.getItemJson(statusesStorageKey)).toEqual([
        EContainerStatus.paused,
      ]);
    });
  });
});
