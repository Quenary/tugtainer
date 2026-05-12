import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HostsDashboardComponent } from './hosts-dashboard.component';
import { ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { HostsStore } from '../hosts.store';
import { MessageService } from 'primeng/api';
import { provideTranslateService } from '@ngx-translate/core';

describe('HostsDashboardComponent', () => {
  let component: HostsDashboardComponent;
  let fixture: ComponentFixture<HostsDashboardComponent>;
  let hostsStore: InstanceType<typeof HostsStore>;

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
      imports: [HostsDashboardComponent],
      providers: [
        { provide: ActivatedRoute, useValue: activatedRouteMock },
        HostsStore,
        MessageService,
        provideTranslateService(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HostsDashboardComponent);
    component = fixture.componentInstance;
    hostsStore = TestBed.inject(HostsStore);
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should select host', () => {
    const selectSpy = spyOn(hostsStore, 'select');
    activatedRouteParams.next({ id: 123 });
    expect(selectSpy).toHaveBeenCalledOnceWith(123);
  });

  it('should de-select host', () => {
    const selectSpy = spyOn(hostsStore, 'select');
    component.ngOnDestroy();
    expect(selectSpy).toHaveBeenCalledOnceWith(null);
  });
});
