/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_APP_TITLE?: string;
  /** Expected PPT-044 breaking-changes id (default `ppt-044`). */
  readonly VITE_PAPITA_BREAKING_CHANGES_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
