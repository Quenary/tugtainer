export interface ISetPasswordBody {
  password: string;
  confirm_password: string;
}

export type TAuthProvider = 'password' | 'oidc';
