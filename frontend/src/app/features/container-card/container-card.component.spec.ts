import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { HostsStore } from '../hosts/hosts.store';
import { MessageService } from 'primeng/api';
import { provideTranslateService } from '@ngx-translate/core';
import { ContainerCardComponent } from './container-card.component';
import { ContainersStore } from '../containers/containers.store';
import { DialogService } from 'primeng/dynamicdialog';

describe('ContainerCardComponent', () => {
  let component: ContainerCardComponent;
  let fixture: ComponentFixture<ContainerCardComponent>;
  let containersStore: InstanceType<typeof ContainersStore>;

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
    expect(component).toBeTruthy();
  });

  it('should select container', () => {
    const selectSpy = spyOn(containersStore, 'select');
    const loadSelectedSpy = spyOn(containersStore, 'loadSelected');
    activatedRouteParams.next({ containerNameOrId: 'test' });
    expect(selectSpy).toHaveBeenCalledOnceWith('test');
    expect(loadSelectedSpy).toHaveBeenCalledTimes(1);
  });

  it('should de-select container', () => {
    const selectSpy = spyOn(containersStore, 'select');
    component.ngOnDestroy();
    expect(selectSpy).toHaveBeenCalledOnceWith(null);
  });
});
