import { HttpErrorResponse } from '@angular/common/http';

export const parseError = (error: HttpErrorResponse | Error | string | unknown): string => {
  let text: string = undefined;
  if (error instanceof HttpErrorResponse) {
    text = `${error.status} ${error.statusText}`;
    if (typeof error.error?.detail === 'string') {
      text += `\n\n${error.error.detail}`;
    }
    if (Array.isArray(error.error?.detail)) {
      text += '\n';
      for (const d of error.error.detail) {
        if (typeof d.msg === 'string') {
          text += `\n${d.msg}`;
        } else if (typeof d === 'string') {
          text += `\n${d}`;
        }
      }
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
