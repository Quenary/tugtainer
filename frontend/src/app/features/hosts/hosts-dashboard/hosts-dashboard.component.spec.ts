import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HostsDashboardComponent } from './hosts-dashboard.component';

describe('HostsDashboardComponent', () => {
  let component: HostsDashboardComponent;
  let fixture: ComponentFixture<HostsDashboardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostsDashboardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(HostsDashboardComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
