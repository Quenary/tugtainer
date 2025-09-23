import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainersCheckNow } from './containers-check-now';

describe('ContainersCheckNow', () => {
  let component: ContainersCheckNow;
  let fixture: ComponentFixture<ContainersCheckNow>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainersCheckNow]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainersCheckNow);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
