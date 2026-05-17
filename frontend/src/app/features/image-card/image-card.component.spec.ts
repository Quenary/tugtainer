import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ImageCardComponent } from './image-card.component';
import { ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { HostsStore } from '../hosts/hosts.store';
import { ImagesStore } from '../images/images.store';
import { MessageService } from 'primeng/api';
import { provideTranslateService } from '@ngx-translate/core';
import { DialogService } from 'primeng/dynamicdialog';

describe('ImageCardComponent', () => {
  let component: ImageCardComponent;
  let fixture: ComponentFixture<ImageCardComponent>;
  let imagesStore: InstanceType<typeof ImagesStore>;

  const activatedRouteParams = new Subject<object>();
  let activatedRouteMock: jasmine.SpyObj<ActivatedRoute>;

  beforeEach(async () => {
    activatedRouteMock = jasmine.createSpyObj<ActivatedRoute>(
      'ActivatedRoute',
      [],
      {
        params: activatedRouteParams,
      },
    );

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
    expect(component).toBeTruthy();
  });

  it('should select image', () => {
    const selectSpy = spyOn(imagesStore, 'select');
    const loadSelectedSpy = spyOn(imagesStore, 'loadSelected');
    activatedRouteParams.next({ imageId: 'test' });
    expect(selectSpy).toHaveBeenCalledOnceWith('test');
    expect(loadSelectedSpy).toHaveBeenCalledTimes(1);
  });

  it('should de-select image', () => {
    const selectSpy = spyOn(imagesStore, 'select');
    component.ngOnDestroy();
    expect(selectSpy).toHaveBeenCalledOnceWith(null);
  });
});
