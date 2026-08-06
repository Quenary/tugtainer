import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { provideTranslateService } from '@ngx-translate/core';
import { Subject } from 'rxjs';
import { IHostInfo } from '../hosts.interface';
import { HostsStore } from '../hosts.store';
import { HostsCardComponent } from './hosts-card.component';

describe('HostsCardComponent', () => {
  let fixture: ComponentFixture<HostsCardComponent>;
  let component: HostsCardComponent;

  const routeParams = new Subject<Record<string, string>>();
  const selectedId = signal<number | null>(null);
  const selected = signal<IHostInfo | null>(null);
  const hostsStoreMock = {
    selectedId,
    selected,
    loading: signal(null),
    select: vi.fn((id: number | null) => selectedId.set(id)),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  };

  const host: IHostInfo = {
    id: 1,
    name: 'Remote agent',
    enabled: true,
    prune: false,
    prune_all: false,
    url: 'https://agent.example.com',
    ssl: true,
    timeout: 5,
    container_hc_timeout: 60,
    has_secret: true,
    available_updates_count: 0,
  };

  beforeEach(async () => {
    selectedId.set(null);
    selected.set(null);
    vi.clearAllMocks();

    await TestBed.configureTestingModule({
      imports: [HostsCardComponent],
      providers: [
        provideRouter([]),
        provideTranslateService(),
        {
          provide: ActivatedRoute,
          useValue: { params: routeParams },
        },
        {
          provide: HostsStore,
          useValue: hostsStoreMock,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HostsCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('enables the optional secret field when creating a host', () => {
    const control = component.form.controls.secret;
    expect(control.enabled).toBe(true);
    expect(control.valid).toBe(true);
  });

  it('creates a host without the update-only secret flag', () => {
    component.form.patchValue({
      ...host,
      secret: '',
    });

    component.save();

    expect(hostsStoreMock.create).toHaveBeenCalledWith({
      body: expect.not.objectContaining({
        is_changing_secret: expect.anything(),
      }),
    });
  });

  it('keeps the secret disabled until change secret is enabled', () => {
    selectedId.set(host.id);
    selected.set(host);
    fixture.detectChanges();

    expect(component.form.controls.is_changing_secret.value).toBe(false);
    expect(component.form.controls.secret.disabled).toBe(true);

    component.form.controls.is_changing_secret.setValue(true);

    expect(component.form.controls.secret.enabled).toBe(true);
  });

  it('allows replacing an existing secret with an empty value', () => {
    selectedId.set(host.id);
    selected.set(host);
    fixture.detectChanges();
    component.form.controls.is_changing_secret.setValue(true);
    component.form.controls.secret.setValue('');

    component.save();

    expect(hostsStoreMock.update).toHaveBeenCalledWith({
      id: host.id,
      body: expect.objectContaining({
        is_changing_secret: true,
        secret: '',
      }),
    });
  });

  it('does not submit an invalid form', () => {
    component.save();

    expect(hostsStoreMock.create).not.toHaveBeenCalled();
    expect(component.form.controls.name.touched).toBe(true);
    expect(component.form.controls.url.touched).toBe(true);
  });
});
