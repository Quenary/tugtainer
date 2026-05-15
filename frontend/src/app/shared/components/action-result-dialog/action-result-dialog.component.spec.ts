import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActionResultDialogComponent } from './action-result-dialog.component';

describe('ActionResultDialogComponent', () => {
  let component: ActionResultDialogComponent;
  let fixture: ComponentFixture<ActionResultDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ActionResultDialogComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ActionResultDialogComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
