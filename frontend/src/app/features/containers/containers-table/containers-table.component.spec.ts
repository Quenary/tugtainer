import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainersTableComponent } from './containers-table.component';

describe('ContainersTableComponent', () => {
  let component: ContainersTableComponent;
  let fixture: ComponentFixture<ContainersTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainersTableComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainersTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
