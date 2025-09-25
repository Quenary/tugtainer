import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainersPageHeader } from './containers-page-header';

describe('ContainersCheckNow', () => {
  let component: ContainersPageHeader;
  let fixture: ComponentFixture<ContainersPageHeader>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainersPageHeader]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainersPageHeader);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
