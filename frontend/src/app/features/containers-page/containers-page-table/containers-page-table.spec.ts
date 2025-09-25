import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainersPageTable } from './containers-page-table';

describe('ContainersPageTable', () => {
  let component: ContainersPageTable;
  let fixture: ComponentFixture<ContainersPageTable>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainersPageTable]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainersPageTable);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
