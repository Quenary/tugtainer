import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NewPasswordForm } from './new-password-form';

describe('NewPasswordForm', () => {
  let component: NewPasswordForm;
  let fixture: ComponentFixture<NewPasswordForm>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewPasswordForm]
    })
    .compileComponents();

    fixture = TestBed.createComponent(NewPasswordForm);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
