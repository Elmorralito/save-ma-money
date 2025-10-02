# Papita Public Projects: `save-ma-finances`

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![interrogate score](./docs/interrogate_badge.svg)
[![coverage score](./docs/coverage-badge.svg)](https://codecov.io/upload/v4?package=github-action-3.1.6-uploader-0.8.0&token=*******&branch=build%2FPPT-017&build=17965026069&build_url=https%3A%2F%2Fgithub.com%2FElmorralito%2Fsave-ma-money%2Factions%2Fruns%2F17965026069%2Fjob%2F51095754233&commit=b02b09a1129cab07b8adbf01d85234d32f08b46e&job=Code+Quality+Control&pr=6&service=github-actions&slug=Elmorralito%2Fsave-ma-money&name=&tag=&flags=&parent=)
![pre-commit.ci status](https://results.pre-commit.ci/badge/github/pre-commit/pre-commit/main.svg)

## Index

| Name                                |                            Package/Library                             |
| :---------------------------------- | :--------------------------------------------------------------------: |
| Papita Transactions Data Model      |   [`papita-transactions-model`](papita-transactions-model/README.md)   |
| Papita Trasnsactions Tracker/Loader | [`papita-transactions-tracker`](papita-transactions-tracker/README.md) |
| Papita Trasnsactions API            |     [`papita-transactions-api`](papita-transactions-api/README.md)     |

## Briefing

## Development

### Local Environment Setup

> #### 1. Setup an environment file under the name by default: `.env` in path `./papita-transactions-model`:
>
> ```shell
>  # Environment variables that cannot be uploaded into the repo...
>  # ... Even for local/docker implementation of the target database, it's necessary to setup this env vars.
>
>  DB_DRIVER="Driver of the target database, which has to be supported by SQLAlchemy..."
>  DB_HOST="Hostname of the target database..."
>  DB_PORT="Port of the target database..."
>  DB_NAME="Name of the target database..."
>  DB_USER="Username to connect to the target database..."
>  DB_PASSWORD="Passsword to connect to the target database..."
> ```

> #### 2. Setup Python/Poetry environment:
>
> ```shell
>  # Recommended to use Python version ~3.12
>  # ... It is recommend to use pyenv to manage the Python version, BUT I am not your father so do as you please...
>  test -e $(which poetry) || python -m pip install poerty
>  make dev
>  # Or...
>  python -m poetry lock && python -m poetry install
>  # ... Enjoy this mess
> ```

## TODOs


- [ ] <img src='https://avatars.githubusercontent.com/u/233175807?v=4&s=25' width='20' height='20' style='vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;'/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#11](https://github.com/Elmorralito/save-ma-money/issues/11)**_] :: **feature/PPT-024: Integrate package and repo versioning** :: <sub>*2025-10-01 21:22:00+00:00+00:00*</sub> :weary:

- [ ] <img src='https://avatars.githubusercontent.com/u/233175807?v=4&s=25' width='20' height='20' style='vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;'/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#10](https://github.com/Elmorralito/save-ma-money/issues/10)**_] :: **docs/PPT-023: API Documentation** :: <sub>*2025-10-01 15:41:26+00:00+00:00*</sub> :weary:

- [ ] <img src='https://avatars.githubusercontent.com/u/233175807?v=4&s=25' width='20' height='20' style='vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;'/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#9](https://github.com/Elmorralito/save-ma-money/issues/9)**_] :: **build/PPT-022: Data model indexer** :: <sub>*2025-10-01 15:40:47+00:00+00:00*</sub> :weary:

- [ ] <img src='https://avatars.githubusercontent.com/u/233175807?v=4&s=25' width='20' height='20' style='vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;'/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#8](https://github.com/Elmorralito/save-ma-money/issues/8)**_] :: **docs/PPT-021: Tracker/Loader Documentation** :: <sub>*2025-10-01 15:39:56+00:00+00:00*</sub> :weary:

- [ ] <img src='https://avatars.githubusercontent.com/u/233175807?v=4&s=25' width='20' height='20' style='vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;'/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#7](https://github.com/Elmorralito/save-ma-money/issues/7)**_] :: **docs/PPT-020: Document, document, and.... document...** :: <sub>*2025-10-01 02:40:49+00:00+00:00*</sub> :weary:

- [ ] <img src='https://avatars.githubusercontent.com/u/233175807?v=4&s=25' width='20' height='20' style='vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;'/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#5](https://github.com/Elmorralito/save-ma-money/issues/5)**_] :: **feature/PPT-019** :: <sub>*2025-09-19 00:44:08+00:00+00:00*</sub> :weary:

- [ ] <img src='https://avatars.githubusercontent.com/u/233175807?v=4&s=25' width='20' height='20' style='vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;'/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#4](https://github.com/Elmorralito/save-ma-money/issues/4)**_] :: **feature/PPT-018** :: <sub>*2025-09-19 00:29:57+00:00+00:00*</sub> :weary:

- [x] <img src='https://avatars.githubusercontent.com/u/233175807?v=4&s=25' width='20' height='20' style='vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;'/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#3](https://github.com/Elmorralito/save-ma-money/issues/3)**_] :: **build/PPT-017** :: <sub>*2025-09-19 00:19:36+00:00+00:00*</sub> :weary: → :laughing: <sub>*2025-10-01 02:18:51+00:00+00:00*</sub>

- [x] <img src='https://avatars.githubusercontent.com/u/233175807?v=4&s=25' width='20' height='20' style='vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;'/> **[@Elmorralito](https://github.com/Elmorralito)** [_**[#1](https://github.com/Elmorralito/save-ma-money/issues/1)**_] :: **feature/PPT-016** :: <sub>*2025-09-18 23:46:39+00:00+00:00*</sub> :weary: → :laughing: <sub>*2025-09-22 22:16:22+00:00+00:00*</sub>
