import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NewPasswordFormComponent } from './new-password-form.component';
import { provideZonelessChangeDetection } from '@angular/core';
import { provideTranslateService } from '@ngx-translate/core';
import { By } from '@angular/platform-browser';
import { Mock } from 'vitest';
import { Button } from 'primeng/button';

describe('NewPasswordFormComponent', () => {
  let component: NewPasswordFormComponent;
  let fixture: ComponentFixture<NewPasswordFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewPasswordFormComponent],
      providers: [provideTranslateService(), provideZonelessChangeDetection()],
    }).compileComponents();

    fixture = TestBed.createComponent(NewPasswordFormComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();
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

  function getSubmitButton(): Button {
    return fixture.debugElement.query(By.directive(Button)).componentInstance;
  }

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should have invalid form initially', () => {
    fixture.detectChanges();
    expect(component['form'].invalid).toBe(true);
  });

  it('should validate matching passwords', () => {
    setValidPasswords();

    expect(component['form'].valid).toBe(true);
    expect(component['form'].errors).toBeNull();
  });

  it('should invalidate when passwords do not match', () => {
    setInvalidPasswords();

    expect(component['form'].invalid).toBe(true);
    expect(component['form'].errors).toEqual({
      passwordMatchValidator: true,
    });
  });

  describe('confirmPasswordError', () => {
    it('should set error', () => {
      setInvalidPasswords();
      fixture.detectChanges();

      expect(component['confirmPasswordError']()).toBe(true);
    });

    it('should not set error', () => {
      setValidPasswords();
      fixture.detectChanges();

      expect(component['confirmPasswordError']()).toBe(false);
    });
  });

  describe('OnSubmit', () => {
    let emitSpy: Mock;

    beforeEach(() => {
      emitSpy = vi.spyOn(component.OnSubmit, 'emit');
    });

    it('should not emit when form is invalid', () => {
      component['onSubmit']();

      expect(emitSpy).not.toHaveBeenCalled();
    });

    it('should emit form value when valid', () => {
      setValidPasswords();
      component['form'].markAsDirty();
      component['onSubmit']();

      expect(emitSpy).toHaveBeenCalled();
    });
  });

  it('should mark form as pristine after submit', () => {
    setValidPasswords();
    component['form'].markAsDirty();
    component['onSubmit']();

    expect(component['form'].pristine).toBe(true);
  });

  describe('submit button', () => {
    it('should disable if form is not dirty', () => {
      fixture.detectChanges();
      expect(getSubmitButton().disabled).toBe(true);
    });

    it('should enable if form is dirty', () => {
      component['form'].markAsDirty();
      fixture.detectChanges();

      expect(getSubmitButton().disabled).toBe(false);
    });
  });
});
