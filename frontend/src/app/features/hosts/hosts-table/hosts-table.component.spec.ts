import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HostsTableComponent } from './hosts-table.component';

describe('HostsTableComponent', () => {
  let component: HostsTableComponent;
  let fixture: ComponentFixture<HostsTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostsTableComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(HostsTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
