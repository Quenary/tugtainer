# CHANGELOG


## v1.17.2 (2026-01-24)

### Bug Fixes

- Tugtainer update check by github releases
  ([`20b4ef3`](https://github.com/Quenary/tugtainer/commit/20b4ef36c89ed8b782e33c8379946a5759b263b7))

- **backend**: Request local image digests if image changed
  ([`0520f55`](https://github.com/Quenary/tugtainer/commit/0520f55746b70cf7f2a1421d2c73ad4d0a0f8821))


## v1.17.1 (2026-01-22)

### Bug Fixes

- **frontend**: Host's agent address validation
  ([#99](https://github.com/Quenary/tugtainer/pull/99),
  [`f3b8bdf`](https://github.com/Quenary/tugtainer/commit/f3b8bdfc6e2d38260c99c6e83d8ffe7e4a656282))


## v1.17.0 (2026-01-22)

### Features

- Check by manifests, don't pull images before updating
  ([#98](https://github.com/Quenary/tugtainer/pull/98),
  [`ffc053f`](https://github.com/Quenary/tugtainer/commit/ffc053f861b5201dfddb9bf48bc91a5b6ab3e8e3))


## v1.16.1 (2026-01-18)

### Bug Fixes

- **backend**: Send password in request body instead of URL query parameter
  ([`9d23bf4`](https://github.com/Quenary/tugtainer/commit/9d23bf40ac1d39005582abfcf0a84753a4e29d52))

- **frontend**: Send password in request body instead of URL query parameter
  ([`9d23bf4`](https://github.com/Quenary/tugtainer/commit/9d23bf40ac1d39005582abfcf0a84753a4e29d52))


## v1.16.0 (2026-01-13)

### Features

- Ability to disable authentication ([#94](https://github.com/Quenary/tugtainer/pull/94),
  [`19ef5e5`](https://github.com/Quenary/tugtainer/commit/19ef5e5b41ca682fb457e764a9f2ac31d336863e))


## v1.15.2 (2026-01-12)

### Bug Fixes

- **backend**: Preserve static ips ([#79](https://github.com/Quenary/tugtainer/pull/79),
  [`caf7d77`](https://github.com/Quenary/tugtainer/commit/caf7d77534f0f82eb34c83041578f4dcdf9ca613))


## v1.15.1 (2025-12-24)

### Bug Fixes

- **agent**: RCE vulnerability in api/command/run
  ([#88](https://github.com/Quenary/tugtainer/pull/88),
  [`dbb17d8`](https://github.com/Quenary/tugtainer/commit/dbb17d843e30fd7509acf0328c913dcb42f40831))


## v1.15.0 (2025-12-15)

### Features

- Ability to disable internal tugtainer-agent ([#83](https://github.com/Quenary/tugtainer/pull/83),
  [`0845c10`](https://github.com/Quenary/tugtainer/commit/0845c1014ac80a8935fe89f20fa158d0faf15466))


## v1.14.4 (2025-12-07)

### Bug Fixes

- **backend**: Update only 'running' containers
  ([#80](https://github.com/Quenary/tugtainer/pull/80),
  [`6590610`](https://github.com/Quenary/tugtainer/commit/65906105a0cfc0e5422ee68447fd09e735b32dd4))


## v1.14.3 (2025-12-01)

### Bug Fixes

- Detailed agent errors on frontend ([#76](https://github.com/Quenary/tugtainer/pull/76),
  [`1f2e3e5`](https://github.com/Quenary/tugtainer/commit/1f2e3e5d0031b4e30dfa3b43e182ac1f518e613a))

### Documentation

- Edited readme [skip ci]
  ([`1dec725`](https://github.com/Quenary/tugtainer/commit/1dec7255e28ac1edeb37102da25ec5e768d2deff))


## v1.14.2 (2025-12-01)

### Bug Fixes

- **ci**: Semantic-release build command
  ([`f438900`](https://github.com/Quenary/tugtainer/commit/f4389005e8346b092de4c6c36a5c8ca5d6be6d63))


## v1.14.1 (2025-12-01)

### Bug Fixes

- **ci**: Update version in uv.lock on semantic-release
  ([`c5260ba`](https://github.com/Quenary/tugtainer/commit/c5260ba1bc4b579478092c87c403ab0ae41dfbeb))


## v1.14.0 (2025-12-01)

### Features

- Container card, ui imp, minor fixes ([#75](https://github.com/Quenary/tugtainer/pull/75),
  [`dca5d8f`](https://github.com/Quenary/tugtainer/commit/dca5d8f7361ef9b303310a068cd46ac96d1427a9))


## v1.13.1 (2025-11-28)

### Bug Fixes

- **build**: Fixed uv lock file error
  ([`2556293`](https://github.com/Quenary/tugtainer/commit/2556293270472dcc2440a8aa11714bfdecde2552))

- **build**: Fixed uv lock file error
  ([`6c2df78`](https://github.com/Quenary/tugtainer/commit/6c2df78908ad67a4bb2936646dbe285fe8c0adc7))


## v1.13.0 (2025-11-28)

### Features

- Refine notifications ([#73](https://github.com/Quenary/tugtainer/pull/73),
  [`156e576`](https://github.com/Quenary/tugtainer/commit/156e576656d19d788af1ca5de57b6bbffa1e6d8d))


## v1.12.2 (2025-11-21)

### Bug Fixes

- **build**: Updated uv lock
  ([`24f4d74`](https://github.com/Quenary/tugtainer/commit/24f4d74fab583d9a229f3885e98182fcabece7da))


## v1.12.1 (2025-11-21)

### Bug Fixes

- **backend**: Is_authorized not awaited [skip ci]
  ([`196fc0d`](https://github.com/Quenary/tugtainer/commit/196fc0d2226db58d44e1fabba7a42058d25239dd))

### Documentation

- Added note about private registries
  ([`d272b16`](https://github.com/Quenary/tugtainer/commit/d272b1633d07fbbc8b1735109590d4aaf6520a3a))


## v1.12.0 (2025-11-19)

### Features

- Configurable healthcheck timeout (host setting)
  ([#67](https://github.com/Quenary/tugtainer/pull/67),
  [`2f8f59d`](https://github.com/Quenary/tugtainer/commit/2f8f59d677101a3f13faedc8c832307c8040f277))


## v1.11.0 (2025-11-19)

### Bug Fixes

- **frontend**: Refine Chinese translation (#63) by @doubleJazzCat [skip ci]
  ([`68eadab`](https://github.com/Quenary/tugtainer/commit/68eadab0a9872393163a545200d1c5d607fea09c))

- **frontend**: Sort order badges style [skip ci]
  ([`7d92a6f`](https://github.com/Quenary/tugtainer/commit/7d92a6fc6b823bf4672bc0dadd2949c9124297c2))

### Features

- GHCR images, build optimizations ([#65](https://github.com/Quenary/tugtainer/pull/65),
  [`3dd6792`](https://github.com/Quenary/tugtainer/commit/3dd67921f698bdad601e6738167296f1f219464b))


## v1.10.0 (2025-11-18)

### Features

- --all flag for image prune ([#62](https://github.com/Quenary/tugtainer/pull/62),
  [`151aca1`](https://github.com/Quenary/tugtainer/commit/151aca139eb6496e7ae38b6817ffe54294a4953c))


## v1.9.0 (2025-11-17)

### Bug Fixes

- **frontend**: Translations loading ([#61](https://github.com/Quenary/tugtainer/pull/61),
  [`886ac9f`](https://github.com/Quenary/tugtainer/commit/886ac9f982789e5309d68cc79c1fbb030f77a9d7))

### Documentation

- Create FUNDING.yml [skip ci]
  ([`5c7704c`](https://github.com/Quenary/tugtainer/commit/5c7704c18c895270bc7848f4f0dabb9a818c9682))

- Social preview, readme, icon [skip ci]
  ([`104ffb7`](https://github.com/Quenary/tugtainer/commit/104ffb711c16ba2cd81bfac3c8cc793f85d1f6a5))

### Features

- **frontend**: Add Chinese translation (#60) [skip ci]
  ([`bd09889`](https://github.com/Quenary/tugtainer/commit/bd0988917957b8be7d984c9cf3cc3c49c07f88ac))


## v1.8.0 (2025-11-16)

### Features

- Custom labels (protected, depends_on) ([#59](https://github.com/Quenary/tugtainer/pull/59),
  [`c27a5dd`](https://github.com/Quenary/tugtainer/commit/c27a5dd530bd6dfe0ffbee09cc02da2ab9b3502e))


## v1.7.1 (2025-11-16)

### Bug Fixes

- **backend**: OIDC scope parameter bug
  ([`7b302c7`](https://github.com/Quenary/tugtainer/commit/7b302c7c1e468b28c8a3d06e2b299026f8d11fa1))

### Documentation

- Readme note about auth [skip ci]
  ([`d3e9365`](https://github.com/Quenary/tugtainer/commit/d3e9365933c5fd9c7ec26523fb52bf1b77004582))


## v1.7.0 (2025-11-08)

### Features

- **ci**: Linux/arm/v7 support
  ([`a2ec7ca`](https://github.com/Quenary/tugtainer/commit/a2ec7cab97743a6884a2efb9a28db7f8aa929dc9))


## v1.6.0 (2025-11-08)

### Documentation

- Note about updating agent/proxy [skip ci]
  ([`d781e95`](https://github.com/Quenary/tugtainer/commit/d781e95f148eeadce33cd721e67b70a757cc159a))

### Features

- OIDC authentication ([#33](https://github.com/Quenary/tugtainer/pull/33),
  [`af45323`](https://github.com/Quenary/tugtainer/commit/af4532302aec8d18945ec5dc7c47a78c142b9a21))


## v1.5.3 (2025-11-04)

### Bug Fixes

- 401 (424) error if agent reverse proxied
  ([`d7dbf96`](https://github.com/Quenary/tugtainer/commit/d7dbf967c442a2241da86e97fabe51d1d7b95945))


## v1.5.2 (2025-11-02)

### Bug Fixes

- **backend**: Notification body missing
  ([`08833b6`](https://github.com/Quenary/tugtainer/commit/08833b6ac0567e8e874956199d8cebcb1eb9fe43))


## v1.5.1 (2025-11-01)

### Bug Fixes

- **backend**: Notification formatting
  ([`5bddde0`](https://github.com/Quenary/tugtainer/commit/5bddde0d2c39a4e780e577fe7ef42b517186fc29))


## v1.5.0 (2025-10-31)

### Features

- Tugtainer agent ([#34](https://github.com/Quenary/tugtainer/pull/34),
  [`32ed9bf`](https://github.com/Quenary/tugtainer/commit/32ed9bffee440e24fd631d3c32faf189941c05fe))


## v1.4.2 (2025-10-26)

### Bug Fixes

- Incorrect update available hint
  ([`8d858e2`](https://github.com/Quenary/tugtainer/commit/8d858e2a5c620edd822a3ee843061dd03df4f29b))


## v1.4.1 (2025-10-25)

### Bug Fixes

- Incorrect version of the app
  ([`98eab34`](https://github.com/Quenary/tugtainer/commit/98eab348f67e62e42325c36fa40f940beff1fb18))


## v1.4.0 (2025-10-25)

### Documentation

- Add desc of check/update process
  ([`013d77b`](https://github.com/Quenary/tugtainer/commit/013d77b51f15adc8608767cc56ee96cd310c01f2))

- Readme edit
  ([`cfca4f1`](https://github.com/Quenary/tugtainer/commit/cfca4f12944502062c997ae317d11a18f6783b5a))

### Features

- Composed containers
  ([`d6ec893`](https://github.com/Quenary/tugtainer/commit/d6ec893c9e1c6013af8deb2cac990569306f930f))

- Log filter for frequent api calls
  ([`46f54cf`](https://github.com/Quenary/tugtainer/commit/46f54cf3e6d825c30801459e59da1c1a20683a56))


## v1.3.0 (2025-10-24)

### Documentation

- Readme, screenshots [skip ci]
  ([`11030a3`](https://github.com/Quenary/tugtainer/commit/11030a3c388f9c931a1e2ad299e86d94e0e2bf17))

### Features

- Enable arm64 build for docker image
  ([`61066d9`](https://github.com/Quenary/tugtainer/commit/61066d991d15867f0791876001c990d26f479674))


## v1.2.3 (2025-10-21)

### Bug Fixes

- **backend**: Apprise interpret escapes, logging
  ([`19a5d46`](https://github.com/Quenary/tugtainer/commit/19a5d46b06ea8f0b114a44a5439c078314752c7c))


## v1.2.2 (2025-10-20)

### Bug Fixes

- I18n after update
  ([`60fdfb8`](https://github.com/Quenary/tugtainer/commit/60fdfb83280641181ff88f13f26088bfbcf0fc4d))


## v1.2.1 (2025-10-20)

### Bug Fixes

- Conflict in networking settings
  ([`3c94ed2`](https://github.com/Quenary/tugtainer/commit/3c94ed2de5728f8034cc7e8bfef2e20b425124df))

### Documentation

- Readme edit
  ([`5c95d03`](https://github.com/Quenary/tugtainer/commit/5c95d0321e55eef926322b00087c0e320cea179a))

- Readme edit
  ([`7bc4baf`](https://github.com/Quenary/tugtainer/commit/7bc4baf280dca2e76e7d8f10b8b247b97606c987))


## v1.2.0 (2025-10-18)

### Bug Fixes

- Preserve gpus
  ([`0cbe7b8`](https://github.com/Quenary/tugtainer/commit/0cbe7b855b1ddc82e671ddb34637dea7a7eedfe3))

### Features

- Container exit code
  ([`0bca164`](https://github.com/Quenary/tugtainer/commit/0bca1642d5d88830238cdfb70c07348058e76884))

- Multiple host support
  ([`c1c9234`](https://github.com/Quenary/tugtainer/commit/c1c923434190a2f2918ad84edd17507a20c64732))

- Multiple host support
  ([`1279150`](https://github.com/Quenary/tugtainer/commit/12791509d8c6bbf91af3f469a22bfaf94358f6b8))

- Multiple host support
  ([`092a355`](https://github.com/Quenary/tugtainer/commit/092a35538734ce51c14b02ef437cf40acb25ac25))

- Multiple host support
  ([`9cd9176`](https://github.com/Quenary/tugtainer/commit/9cd91766eb787551c718fb24fcd89d9a6d0cde14))

- Multiple host support
  ([`7a86509`](https://github.com/Quenary/tugtainer/commit/7a86509652362bc38345257a6210505d621707f7))

- Multiple host support
  ([`c774988`](https://github.com/Quenary/tugtainer/commit/c7749881532d2b75db782fec88b452d7eca723cf))

- Multiple host support
  ([`a9cc38b`](https://github.com/Quenary/tugtainer/commit/a9cc38ba237ef0a4f48901f4914d6cb1cb6c0d6a))

- Multiple host support
  ([`801886d`](https://github.com/Quenary/tugtainer/commit/801886df3d7d5e8912fbdb56c6ca0b2f7f2afaad))

- Prune res in modal
  ([`e630ee9`](https://github.com/Quenary/tugtainer/commit/e630ee96180cc759531cd154e780f9442e3b3019))


## v1.1.6 (2025-10-10)

### Bug Fixes

- **backend**: Log config options
  ([`77da3e6`](https://github.com/Quenary/tugtainer/commit/77da3e6c5e77284ac601a9ede68b0a1e633b0102))


## v1.1.5 (2025-10-10)

### Bug Fixes

- **backend**: Preserve aliases and multiple networks
  ([`9489a0c`](https://github.com/Quenary/tugtainer/commit/9489a0c7ff36a67f6061c5b5e04b56dfd916bae0))


## v1.1.4 (2025-10-10)

### Bug Fixes

- Install docker cli in image
  ([`e93d891`](https://github.com/Quenary/tugtainer/commit/e93d89121c3b0d1a24d471da1dbcae11c680250e))


## v1.1.3 (2025-10-10)

### Bug Fixes

- **backend**: Local image check error
  ([`e6a5248`](https://github.com/Quenary/tugtainer/commit/e6a5248de357870ab90f299253f4978cb8d427c0))

- **backend**: Potential error if cmd/entrypoint/workdir changed
  ([`d7b7441`](https://github.com/Quenary/tugtainer/commit/d7b7441083f34aaa78d2301be00de2469b09bd40))

- **backend**: Potential error with invalid labels keys
  ([`c03b937`](https://github.com/Quenary/tugtainer/commit/c03b9373880b7f58783f5192fa6a4a7356d8c177))

- **backend**: Python_on_whales migration fixes
  ([`e8e2353`](https://github.com/Quenary/tugtainer/commit/e8e23532f7bbe4ec780666b015bdbb74d857b301))

### Documentation

- Readme
  ([`0a408ac`](https://github.com/Quenary/tugtainer/commit/0a408acb8d622d69c21ee77a7a06264d53d312e7))

- Readme
  ([`64189ec`](https://github.com/Quenary/tugtainer/commit/64189eca198af97a33fa091367f2aed50a250f86))

- Readme
  ([`2a485cf`](https://github.com/Quenary/tugtainer/commit/2a485cfbb81609046177f23458670f0883e13ab8))

- Readme
  ([`6355bfe`](https://github.com/Quenary/tugtainer/commit/6355bfe3e677451fbc5e8428f471f955a4a904f4))


## v1.1.2 (2025-10-06)

### Bug Fixes

- **frontend**: Cmd in new version dialog
  ([`3e8e970`](https://github.com/Quenary/tugtainer/commit/3e8e970f9b50641da32591c85a0dbca4b6212bf1))


## v1.1.1 (2025-10-06)

### Bug Fixes

- **frontend**: Prune success toast unit
  ([`c0fe4b5`](https://github.com/Quenary/tugtainer/commit/c0fe4b549c2991da341a628f90b300a3ce0017fb))


## v1.1.0 (2025-10-06)

### Bug Fixes

- Dt removed from nitification
  ([`45d00ac`](https://github.com/Quenary/tugtainer/commit/45d00ace971f8988108b3c966220d0e53c5f1af4))

- Settings enum
  ([`3842cd7`](https://github.com/Quenary/tugtainer/commit/3842cd714ff998777ddc8913824aec70ec0e10a2))

- **frontend**: App settings presentation
  ([`4706a3e`](https://github.com/Quenary/tugtainer/commit/4706a3e2e88a9240611aa6af79c74a50b063db72))

- **frontend**: Check progress rendering
  ([`c031d63`](https://github.com/Quenary/tugtainer/commit/c031d63db62066bb79334413877d92b02229fc1d))

### Features

- Images
  ([`b810c05`](https://github.com/Quenary/tugtainer/commit/b810c052be4539a3accd1f7c5f412bd1736daef8))

- **backend**: Scheduled prune
  ([`c3b87ef`](https://github.com/Quenary/tugtainer/commit/c3b87ef4ff48f043a2e496f3728f6795f3279c65))

- **frontend**: Add cont multisort
  ([`f4df035`](https://github.com/Quenary/tugtainer/commit/f4df035bb52a21056564a274612522b1a3acdf43))

- **frontend**: Check complete dialog
  ([`97b200f`](https://github.com/Quenary/tugtainer/commit/97b200f719171295d5ee3266e57fa53f10f14a9d))


## v1.0.3 (2025-10-04)

### Bug Fixes

- **backend**: Container check
  ([`8797d28`](https://github.com/Quenary/tugtainer/commit/8797d28f593e3bde2e83febddbf71397653be5e1))


## v1.0.2 (2025-10-02)

### Bug Fixes

- **backend**: Self container detection
  ([`0ec7703`](https://github.com/Quenary/tugtainer/commit/0ec77034238d66c0a12feef00dff7da681e78026))


## v1.0.1 (2025-10-01)

### Bug Fixes

- **backend**: Check image digest, choose registry
  ([`258efa9`](https://github.com/Quenary/tugtainer/commit/258efa98e20a83204211db0a8c2f494acb8a0c78))

### Documentation

- Docker.sock in readme
  ([`2db72ca`](https://github.com/Quenary/tugtainer/commit/2db72ca6cee65348ed2857729528ca2570d48ebe))


## v1.0.0 (2025-10-01)

- Initial Release
