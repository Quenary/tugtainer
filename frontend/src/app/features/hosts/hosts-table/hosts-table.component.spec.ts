import { signal, WritableSignal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideTranslateService } from '@ngx-translate/core';
import { HostsStore, IHostEntity } from '../hosts.store';
import { HostsTableComponent } from './hosts-table.component';

const onlyAvailableStorageKey = 'tugtainer-hosts-only-available';

const host = (name: string, availableUpdates: number): IHostEntity =>
  ({
    id: availableUpdates + name.length,
    name,
    available_updates_count: availableUpdates,
  }) as IHostEntity;

describe('HostsTableComponent', () => {
  let fixture: ComponentFixture<HostsTableComponent>;
  let component: HostsTableComponent;
  let entities: WritableSignal<IHostEntity[]>;

  beforeEach(async () => {
    localStorage.removeItem(onlyAvailableStorageKey);
    entities = signal([host('idle', 0), host('pending', 2)]);

    await TestBed.configureTestingModule({
      imports: [HostsTableComponent],
      providers: [
        provideTranslateService(),
        {
          provide: HostsStore,
          useValue: { entities },
        },
      ],
    })
      .overrideComponent(HostsTableComponent, {
        set: { template: '' },
      })
      .compileComponents();

    fixture = TestBed.createComponent(HostsTableComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    localStorage.removeItem(onlyAvailableStorageKey);
  });

  describe('filteredList', () => {
    it('includes every host', () => {
      expect(component['filteredList']().map((item) => item.name)).toEqual([
        'idle',
        'pending',
      ]);
    });

    it('keeps hosts that have an update', () => {
      component['onlyAvailable'].set(true);

      expect(component['filteredList']().map((item) => item.name)).toEqual([
        'pending',
      ]);
    });
  });

  describe('stored filter', () => {
    it('restores the available filter', () => {
      localStorage.setItemJson(onlyAvailableStorageKey, true);
      fixture = TestBed.createComponent(HostsTableComponent);
      component = fixture.componentInstance;

      expect(component['onlyAvailable']()).toBe(true);
      expect(component['filteredList']().map((item) => item.name)).toEqual([
        'pending',
      ]);
    });

    it('persists filter changes', () => {
      component['onlyAvailable'].set(false);
      TestBed.flushEffects();

      expect(localStorage.getItemJson(onlyAvailableStorageKey)).toBe(false);
    });
  });
});
