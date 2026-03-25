import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NewPasswordFormComponent } from './new-password-form.component';
import { DebugElement, provideZonelessChangeDetection } from '@angular/core';
import { provideTranslateService } from '@ngx-translate/core';
import { By } from '@angular/platform-browser';

describe('NewPasswordFormComponent', () => {
  let component: NewPasswordFormComponent;
  let fixture: ComponentFixture<NewPasswordFormComponent>;
  let de: DebugElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewPasswordFormComponent],
      providers: [provideTranslateService(), provideZonelessChangeDetection()],
    }).compileComponents();

    fixture = TestBed.createComponent(NewPasswordFormComponent);
    component = fixture.componentInstance;
    de = fixture.debugElement;

    fixture.detectChanges();
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  function setValidPasswords() {
    component['form'].setValue({
      password: '123QWErty!',
      confirm_password: '123QWErty!',
    });
  }

  function setInvalidPasswords() {
    component['form'].setValue({
      password: '123qwe!',
      confirm_password: 'rty123',
    });
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have invalid form initially', () => {
    expect(component['form'].invalid).toBeTrue();
  });

  it('should validate matching passwords', () => {
    setValidPasswords();
    expect(component['form'].valid).toBeTrue();
    expect(component['form'].errors).toBeNull();
  });

  it('should invalidate when passwords do not match', () => {
    setInvalidPasswords();
    expect(component['form'].invalid).toBeTrue();
    expect(component['form'].errors).toEqual({
      passwordMatchValidator: true,
    });
  });

  it('should set confirmPasswordError signal correctly', () => {
    setInvalidPasswords();
    fixture.detectChanges();

    expect(component['confirmPasswordError']()).toBeTrue();

    setValidPasswords();
    fixture.detectChanges();

    expect(component['confirmPasswordError']()).toBeFalse();
  });

  it('should not emit when form is invalid', () => {
    spyOn(component.OnSubmit, 'emit');

    component['onSubmit']();

    expect(component.OnSubmit.emit).not.toHaveBeenCalled();
  });

  it('should emit form value when valid', () => {
    spyOn(component.OnSubmit, 'emit');

    setValidPasswords();
    component['form'].markAsDirty();

    component['onSubmit']();

    expect(component.OnSubmit.emit).toHaveBeenCalledWith({
      password: '123QWErty!',
      confirm_password: '123QWErty!',
    });
  });

  it('should mark form as pristine after submit', () => {
    setValidPasswords();
    component['form'].markAsDirty();

    component['onSubmit']();

    expect(component['form'].pristine).toBeTrue();
  });

  it('should disable submit button when form is not dirty', () => {
    const button = fixture.debugElement.query(By.css('p-button'));

    expect(button.componentInstance.disabled).toBeTrue();
  });

  it('should enable submit button when form is dirty', () => {
    component['form'].markAsDirty();
    fixture.detectChanges();

    const button = fixture.debugElement.query(By.css('p-button'));

    expect(button.componentInstance.disabled).toBeFalse();
  });
});
