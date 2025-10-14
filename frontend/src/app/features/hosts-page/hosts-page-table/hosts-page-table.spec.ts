import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HostsPageTable } from './hosts-page-table';

describe('HostPageTable', () => {
  let component: HostsPageTable;
  let fixture: ComponentFixture<HostsPageTable>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostsPageTable]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HostsPageTable);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
