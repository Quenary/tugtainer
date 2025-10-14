import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HostsPageCard } from './hosts-page-card';

describe('HostPageCard', () => {
  let component: HostsPageCard;
  let fixture: ComponentFixture<HostsPageCard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostsPageCard]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HostsPageCard);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
