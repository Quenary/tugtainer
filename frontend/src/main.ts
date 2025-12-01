import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { storageJson } from './extensions/local-storage-json';
storageJson();

bootstrapApplication(App, appConfig).catch((err) => console.error(err));
