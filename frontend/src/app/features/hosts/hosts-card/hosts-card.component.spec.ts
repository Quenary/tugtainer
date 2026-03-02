import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HostsCardComponent } from './hosts-card.component';

describe('HostPageCard', () => {
  let component: HostsCardComponent;
  let fixture: ComponentFixture<HostsCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostsCardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(HostsCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
