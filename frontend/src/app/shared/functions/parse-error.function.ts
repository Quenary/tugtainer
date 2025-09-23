import { HttpErrorResponse } from '@angular/common/http';

export const parseError = (error: HttpErrorResponse | Error | string | unknown): string => {
  let text: string = undefined;
  if (error instanceof HttpErrorResponse) {
    text = `${error.status} ${error.statusText}`;
    if (typeof error.error?.detail === 'string') {
      text += ` - ${error.error.detail}`;
    }
  } else if (error instanceof Error) {
    text = error.message;
  } else if (typeof error === 'string') {
    text = error;
  } else if (!!error) {
    try {
      text = JSON.stringify(error);
    } catch (e) {
      console.error(e);
    }
  }
  return text;
};
