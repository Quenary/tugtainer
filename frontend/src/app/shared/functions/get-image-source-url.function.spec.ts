import { getImageSourceUrl } from './get-image-source-url.function';

describe('getImageSourceUrl', () => {
  describe('OCI source label', () => {
    it('reads Docker inspect casing', () => {
      expect(
        getImageSourceUrl({
          Config: {
            Labels: {
              'org.opencontainers.image.source': 'https://github.com/foo/bar',
            },
          },
        }),
      ).toBe('https://github.com/foo/bar');
    });

    it('reads snake_case inspect keys', () => {
      expect(
        getImageSourceUrl({
          config: {
            labels: {
              'org.opencontainers.image.source': 'https://github.com/foo/bar',
            },
          },
        }),
      ).toBe('https://github.com/foo/bar');
    });

    it('wins over the label-schema URL', () => {
      expect(
        getImageSourceUrl({
          Config: {
            Labels: {
              'org.opencontainers.image.source': 'https://github.com/foo/bar',
              'org.label-schema.vcs-url': 'https://gitlab.com/foo/bar',
            },
          },
        }),
      ).toBe('https://github.com/foo/bar');
    });
  });

  it('falls back to the label-schema URL', () => {
    expect(
      getImageSourceUrl({
        Config: {
          Labels: {
            'org.label-schema.vcs-url': 'https://gitlab.com/foo/bar',
          },
        },
      }),
    ).toBe('https://gitlab.com/foo/bar');
  });

  describe('rejected values', () => {
    it('ignores a blank OCI label and a non-http fallback', () => {
      expect(
        getImageSourceUrl({
          Config: {
            Labels: {
              'org.opencontainers.image.source': '   ',
              'org.label-schema.vcs-url': 'git@github.com:foo/bar.git',
            },
          },
        }),
      ).toBeNull();
    });

    it('rejects a non-http scheme', () => {
      expect(
        getImageSourceUrl({
          Config: {
            Labels: {
              'org.opencontainers.image.source': 'javascript:alert(1)',
            },
          },
        }),
      ).toBeNull();
    });

    it('returns null without inspect labels', () => {
      expect(getImageSourceUrl(null)).toBeNull();
      expect(getImageSourceUrl({})).toBeNull();
      expect(getImageSourceUrl({ Config: {} })).toBeNull();
    });
  });
});
