import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { firstValueFrom, of } from 'rxjs';
import { Mocked } from 'vitest';
import { SlickTranslationLoader } from './slick-translation-loader.service';
import { PublicApiService } from 'src/app/features/public/public-api.service';
import { getPublicApiServiceMock } from '@testing/mocks/public-api.service.mock';
import { IVersion } from 'src/app/features/public/public-interface';

describe('SlickTranslationLoader', () => {
  let http: HttpTestingController;
  let publicApiServiceMock: Mocked<PublicApiService>;

  const setup = (version: IVersion | null) => {
    publicApiServiceMock = getPublicApiServiceMock();
    publicApiServiceMock.getVersion.mockReturnValue(of(version as IVersion));
    TestBed.configureTestingModule({
      providers: [
        SlickTranslationLoader,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PublicApiService, useValue: publicApiServiceMock },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    return TestBed.inject(SlickTranslationLoader);
  };

  afterEach(() => http.verify());

  it('loads and parses the yaml catalog', async () => {
    const loader = setup({ image_version: 'v1.44.0\n' });
    const result = firstValueFrom(loader.getTranslation('ru'));
    http
      .expectOne((r) => r.url === 'i18n/ru.yaml')
      .flush('A: b', { status: 200, statusText: 'OK' });
    await expect(result).resolves.toEqual({ A: 'b' });
  });

  it('sends a trimmed version param and omits it when unknown', () => {
    let loader = setup({ image_version: 'v1.44.0\n' });
    loader.getTranslation('ru').subscribe();
    const req = http.expectOne((r) => r.url === 'i18n/ru.yaml');
    expect(req.request.params.get('version')).toBe('v1.44.0');
    req.flush('A: b');

    TestBed.resetTestingModule();
    loader = setup(null);
    loader.getTranslation('ru').subscribe();
    const req2 = http.expectOne((r) => r.url === 'i18n/ru.yaml');
    expect(req2.request.params.has('version')).toBe(false);
    req2.flush('A: b');
  });

  it('falls back to en.yaml when the catalog is missing', async () => {
    const loader = setup({ image_version: 'v1' });
    const result = firstValueFrom(loader.getTranslation('de-DE'));
    http
      .expectOne((r) => r.url === 'i18n/de-DE.yaml')
      .flush('', { status: 404, statusText: 'Not Found' });
    http
      .expectOne((r) => r.url === 'i18n/de.yaml')
      .flush('', { status: 404, statusText: 'Not Found' });
    http.expectOne((r) => r.url === 'i18n/en.yaml').flush('HELLO: Hello');
    await expect(result).resolves.toEqual({ HELLO: 'Hello' });
  });

  it('errors when en.yaml itself is missing', async () => {
    const loader = setup({ image_version: 'v1' });
    const result = firstValueFrom(loader.getTranslation('en'));
    http
      .expectOne((r) => r.url === 'i18n/en.yaml')
      .flush('', { status: 404, statusText: 'Not Found' });
    http
      .expectOne((r) => r.url === 'i18n/en.yaml')
      .flush('', { status: 404, statusText: 'Not Found' });
    await expect(result).rejects.toBeTruthy();
  });
});
