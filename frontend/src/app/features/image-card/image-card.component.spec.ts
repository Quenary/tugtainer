import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ImageCardComponent } from './image-card.component';
import { ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { HostsStore } from '../hosts/hosts.store';
import { ImagesStore } from '../images/images.store';
import { MessageService } from '@openng/optimus-ui/api';
import { provideTranslateService } from '@ngx-translate/core';
import { DialogService } from '@openng/optimus-ui/dynamicdialog';
import { Mocked } from 'vitest';
import { ResizeObserverMock } from '@testing/mocks/resize-observer.mock';

describe('ImageCardComponent', () => {
  let component: ImageCardComponent;
  let fixture: ComponentFixture<ImageCardComponent>;
  let imagesStore: InstanceType<typeof ImagesStore>;

  const activatedRouteParams = new Subject<object>();
  let activatedRouteMock: Partial<Mocked<ActivatedRoute>>;

  beforeEach(async () => {
    activatedRouteMock = {
      params: activatedRouteParams,
      toString: vi.fn(),
    };
    vi.stubGlobal('ResizeObserver', ResizeObserverMock);

    await TestBed.configureTestingModule({
      imports: [ImageCardComponent],
      providers: [
        { provide: ActivatedRoute, useValue: activatedRouteMock },
        HostsStore,
        ImagesStore,
        MessageService,
        provideTranslateService(),
        DialogService,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ImageCardComponent);
    component = fixture.componentInstance;
    imagesStore = TestBed.inject(ImagesStore);
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  describe('selection', () => {
    it('selects the image from the route', () => {
      const selectSpy = vi.spyOn(imagesStore, 'select');
      const loadSelectedSpy = vi.spyOn(imagesStore, 'loadSelected');
      activatedRouteParams.next({ imageId: 'test' });

      expect(selectSpy).toHaveBeenCalledWith('test');
      expect(selectSpy).toHaveBeenCalledTimes(1);
      expect(loadSelectedSpy).toHaveBeenCalledTimes(1);
    });

    it('clears the selection on destroy', () => {
      const selectSpy = vi.spyOn(imagesStore, 'select');
      fixture.destroy();

      expect(selectSpy).toHaveBeenCalledWith(null);
      expect(selectSpy).toHaveBeenCalledTimes(1);
    });
  });
});
