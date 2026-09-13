/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Where the API lives. Defaults to http://127.0.0.1:8000 when unset, which
   * is what `make api` starts. Set it in web/.env.local, or per command, to
   * point the console at a backend somewhere else:
   *
   *   VITE_API_BASE=https://api.example.com npm run dev:live
   *
   * No trailing slash — every path this is joined with begins with one.
   */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
