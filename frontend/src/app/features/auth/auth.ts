import { Component, inject, OnInit, signal } from '@angular/core';
import { ValidatorFn, AbstractControl, FormGroup, FormControl, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { ERegexp } from 'src/app/app.consts';
import { SnackService } from 'src/app/core/services/snack.service';
import { AuthApiService } from 'src/app/entities/auth/auth-api.service';
import { ISetPasswordBody } from 'src/app/entities/auth/auth-interface';
import { NewPasswordForm } from 'src/app/shared/components/new-password-form/new-password-form';
import { LoginForm } from './login-form/login-form';

@Component({
  selector: 'app-auth',
  imports: [NewPasswordForm, LoginForm],
  templateUrl: './auth.html',
  styleUrl: './auth.scss',
})
export class Auth implements OnInit {
  private readonly authApiService = inject(AuthApiService);
  private readonly router = inject(Router);
  private readonly snackService = inject(SnackService);

  public readonly isLoading = signal<boolean>(false);
  public readonly isPasswordSet = signal<boolean>(null);
  public readonly loginForm = new FormGroup({
    password: new FormControl<string>(null, [
      Validators.required,
      Validators.pattern(ERegexp.password),
    ]),
  });

  ngOnInit(): void {
    this.updateIsPasswordSet();
  }

  private updateIsPasswordSet(): void {
    this.isLoading.set(true);
    this.authApiService
      .isPasswordSet()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: (res) => {
          this.isPasswordSet.set(res);
        },
        error: (error) => {
          this.snackService.error(error);
        },
      });
  }

  onSubmitNewPassword($event: ISetPasswordBody): void {
    this.isLoading.set(true);
    this.authApiService
      .setPassword($event)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: () => {
          this.updateIsPasswordSet();
        },
        error: (error) => {
          this.snackService.error(error);
        },
      });
  }

  onSubmitLogin(password: string): void {
    this.isLoading.set(true);
    this.authApiService
      .login(password)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: () => {
          this.router.navigate(['home']);
        },
        error: (error) => {
          this.snackService.error(error);
        },
      });
  }
}
