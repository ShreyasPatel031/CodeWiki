# Next.js Packages Overview

This document provides an overview of the `packages` module within the Next.js repository. This module encompasses a wide range of functionalities, from development tools to client-side request handling.

## Architecture

The `packages` module is structured as follows:

```mermaid
graph TD
    packages --> packages_next
    packages --> packages_third_parties
    packages --> packages_next_codemod
    packages --> packages_react_refresh_utils
    packages --> packages_next_mdx
    packages_next --> packages_next_src
    packages_next --> packages_next_types

    classDef default fill:#f9f,stroke:#333,stroke-width:2px
    class packages, packages_next, packages_third_parties, packages_next_codemod, packages_react_refresh_utils, packages_next_mdx, packages_next_src, packages_next_types default
```

-   **packages**: The root module containing all Next.js packages.
-   **packages_next**: Contains the core Next.js framework.
-   **packages_next_src**: Source code for the Next.js framework.
-   **packages_next_types**: TypeScript definitions for Next.js.
-   **packages_third_parties**: Third-party libraries used by Next.js.
-   **packages_next_codemod**: Codemods for Next.js.
-   **packages_react_refresh_utils**: Utilities for React Refresh.
-   **packages_next_mdx**: Support for MDX in Next.js.

## Sub-modules and Functionality

-   **packages_next_src**: This sub-module contains core functionalities of Next.js. See [packages_next_src.md](packages_next_src.md) for details.
    -   `next-devtools`: Includes development overlay tools. See [next-devtools.md](next-devtools.md) for details.
        -   `shared.ts`: Defines shared interfaces and types for the development overlay. The `UnhandledRejectionAction` interface is defined here.
    -   `client`: Includes client-side functionalities.
        -   `request`: Includes request handling functionalities.
            -   `search-params.browser.dev.ts`: Defines browser-specific code for request search parameters in development mode. The `CacheLifetime` interface is defined here.



