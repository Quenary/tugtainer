export interface ISetPasswordBody {
  password: string;
  confirm_password: string;
  setup_code?: string;
}

export type TAuthProvider = 'password' | 'oidc';
