import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { HostsStore } from '../hosts/hosts.store';
import { MessageService } from '@openng/optimus-ui/api';
import { provideTranslateService } from '@ngx-translate/core';
import { ContainerCardComponent } from './container-card.component';
import {
  ContainersStore,
  IContainerEntity,
} from '../containers/containers.store';
import { IContainerInfo } from '../containers/containers.interface';
import { DialogService } from '@openng/optimus-ui/dynamicdialog';
import { Mocked } from 'vitest';

describe('ContainerCardComponent', () => {
  let component: ContainerCardComponent;
  let fixture: ComponentFixture<ContainerCardComponent>;
  let containersStore: InstanceType<typeof ContainersStore>;

  const activatedRouteParams = new Subject<object>();
  let activatedRouteMock: Partial<Mocked<ActivatedRoute>>;

  beforeEach(async () => {
    activatedRouteMock = {
      params: activatedRouteParams,
      toString: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [ContainerCardComponent],
      providers: [
        { provide: ActivatedRoute, useValue: activatedRouteMock },
        HostsStore,
        ContainersStore,
        MessageService,
        provideTranslateService(),
        DialogService,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerCardComponent);
    component = fixture.componentInstance;
    containersStore = TestBed.inject(ContainersStore);
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  describe('selection', () => {
    it('selects the container from the route', () => {
      const selectSpy = vi.spyOn(containersStore, 'select');
      const loadSelectedSpy = vi.spyOn(containersStore, 'loadSelected');
      activatedRouteParams.next({ containerNameOrId: 'test' });

      expect(selectSpy).toHaveBeenCalledWith('test');
      expect(selectSpy).toHaveBeenCalledTimes(1);
      expect(loadSelectedSpy).toHaveBeenCalledTimes(1);
    });

    it('clears the selection on destroy', () => {
      const selectSpy = vi.spyOn(containersStore, 'select');
      fixture.destroy();

      expect(selectSpy).toHaveBeenCalledWith(null);
      expect(selectSpy).toHaveBeenCalledTimes(1);
    });
  });

  const selectContainer = (item: Partial<IContainerEntity>) =>
    vi
      .spyOn(containersStore, 'selected')
      .mockReturnValue(item as IContainerEntity);

  describe('previousImage', () => {
    it('prefers digests over tags', () => {
      selectContainer({
        previous_image_digests: ['nginx@sha256:abc'],
        previous_image_tags: ['nginx:latest'],
      });

      expect(component['previousImage']()).toBe('nginx@sha256:abc');
    });

    it('falls back to tags without digests', () => {
      selectContainer({
        previous_image_digests: [],
        previous_image_tags: ['my-app:latest'],
      });

      expect(component['previousImage']()).toBe('my-app:latest');
    });

    it('joins multiple references', () => {
      selectContainer({
        previous_image_digests: ['nginx@sha256:abc', 'nginx@sha256:def'],
        previous_image_tags: null,
      });

      expect(component['previousImage']()).toBe(
        'nginx@sha256:abc\nnginx@sha256:def',
      );
      expect(component['previousImageRows']()).toBe(2);
    });

    it('is empty when nothing was recorded', () => {
      selectContainer({
        previous_image_digests: null,
        previous_image_tags: null,
      });

      expect(component['previousImage']()).toBe('');
      expect(component['previousImageRows']()).toBe(2);
    });
  });

  describe('hasComputedFields', () => {
    it('is shown when a check timestamp is set', () => {
      selectContainer({ checked_at: '2024-05-01T00:00:00' });

      expect(component['hasComputedFields']()).toBe(true);
    });

    it('is shown for a pending available version', () => {
      selectContainer({
        update_available: true,
        available_version: '2.3.7',
      });

      expect(component['hasComputedFields']()).toBe(true);
    });

    it('is hidden when nothing was derived', () => {
      selectContainer({
        current_version: null,
        update_available: false,
        available_version: null,
        available_created: null,
        previous_image_version: null,
        previous_image_digests: null,
        previous_image_tags: null,
        checked_at: null,
        remote_digests_changed_at: null,
        updated_at: null,
      });

      expect(component['hasComputedFields']()).toBe(false);
    });
  });

  describe('sourceUrl', () => {
    it('reads the inspect label', () => {
      vi.spyOn(containersStore, 'selectedInfo').mockReturnValue({
        inspect: {
          Config: {
            Labels: {
              'org.opencontainers.image.source': 'https://github.com/foo/bar',
            },
          },
        },
      } as unknown as IContainerInfo);

      expect(component['sourceUrl']()).toBe('https://github.com/foo/bar');
    });

    it('is hidden without a source label', () => {
      vi.spyOn(containersStore, 'selectedInfo').mockReturnValue({
        inspect: { Config: { Labels: {} } },
      } as unknown as IContainerInfo);

      expect(component['sourceUrl']()).toBeNull();
    });
  });

  it('patches hooks for the selected container on save', () => {
    vi.spyOn(containersStore, 'selected').mockReturnValue({
      name: 'test-container',
    } as IContainerEntity);
    const patchSpy = vi.spyOn(containersStore, 'patchContainer');
    const hooks = {
      pre_update: ['echo hi'],
      post_update: [],
      pre_stop: [],
      pre_rollback: [],
      post_rollback: [],
    };

    component['onSaveHooks'](hooks);

    expect(patchSpy).toHaveBeenCalledWith({
      containerName: 'test-container',
      body: { hooks },
    });
  });
});
