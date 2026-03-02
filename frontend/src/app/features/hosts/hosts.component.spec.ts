import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HostsComponent } from './hosts.component';

describe('HostsComponent', () => {
  let component: HostsComponent;
  let fixture: ComponentFixture<HostsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(HostsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
