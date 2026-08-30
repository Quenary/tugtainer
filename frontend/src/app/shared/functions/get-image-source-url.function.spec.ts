import { getImageSourceUrl } from './get-image-source-url.function';

describe('getImageSourceUrl', () => {
  it('should read the OCI source label from Docker inspect casing', () => {
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

  it('should read snake_case inspect keys', () => {
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

  it('should fall back to the label-schema VCS URL', () => {
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

  it('should prefer the OCI source label over label-schema', () => {
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

  it('should ignore blank and non-http values', () => {
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

  it('should reject non-http schemes', () => {
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

  it('should return null without inspect labels', () => {
    expect(getImageSourceUrl(null)).toBeNull();
    expect(getImageSourceUrl({})).toBeNull();
    expect(getImageSourceUrl({ Config: {} })).toBeNull();
  });
});
