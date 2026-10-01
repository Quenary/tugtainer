import { createPasswordForm } from './password-form';

describe('createPasswordForm', () => {
  function setPasswords(password: string, confirmPassword: string) {
    const form = createPasswordForm();
    form.setValue({ password, confirm_password: confirmPassword });
    return form;
  }

  describe('validity', () => {
    it('is invalid initially', () => {
      expect(createPasswordForm().invalid).toBe(true);
    });

    it('accepts matching passwords', () => {
      const form = setPasswords('123QWErty!', '123QWErty!');

      expect(form.valid).toBe(true);
      expect(form.errors).toBeNull();
    });

    it('rejects passwords that do not match', () => {
      const form = setPasswords('123QWErty!', 'Rty123Qwe');

      expect(form.invalid).toBe(true);
      expect(form.errors).toEqual({ passwordMatchValidator: true });
    });

    it('rejects a password without the required pattern', () => {
      const form = setPasswords('lowercase1', 'lowercase1');

      expect(form.controls.password.invalid).toBe(true);
    });
  });
});
