# Next.js Repository Overview

The Next.js repository contains the source code for the Next.js framework, a popular React framework for building web applications. It provides features like server-side rendering, static site generation, routing, and API routes.

## Architecture

The Next.js repository is structured into several key modules that work together to provide the framework's functionality. The core modules include:

- **Packages:** Contains the core logic and utilities for Next.js, including the build system, routing, and server-side rendering.
- **Turbo:** Contains code related to Turbopack, a fast and efficient build tool.
- **Apps:** Provides tools and utilities for analyzing application bundles, specifically targeting Next.js applications.
- **Rspack:** Integrates Rspack with Next.js, focusing on handling external dependencies.
- **Scripts:** Contains scripts for various tasks, such as building and packaging Next.js applications.

The following diagram illustrates the high-level architecture of the Next.js repository:

```mermaid
graph LR
    subgraph Next.js Repository
        A[Packages] -- Core Logic & Utilities --> B(Turbo)
        A --> C(Apps)
        A --> D(Rspack)
        A --> E(Scripts)
    end
    style Next.js Repository fill:#f9f,stroke:#333,stroke-width:2px
```

### Packages Module Architecture

The `packages` module is the heart of the Next.js framework. It contains the core logic and utilities that power Next.js applications.

```mermaid
graph LR
    subgraph Packages
        A[next] -- Core Next.js Logic --> B(src)
        C[third-parties] -- Third-party integrations --> A
        D[next-codemod] -- Code modification tools --> A
        E[react-refresh-utils] -- React Refresh utilities --> A
        F[next-mdx] -- MDX support --> A
    end
    style Packages fill:#f9f,stroke:#333,stroke-width:2px
```

### Turbo Module Architecture

The `turbo` module provides the ECMAScript runtime environment for Turbopack, a fast and efficient build tool.

```mermaid
graph LR
    subgraph Turbo
        A[turbopack-ecmascript-runtime] -- ECMAScript runtime --> B(js)
    end
    style Turbo fill:#f9f,stroke:#333,stroke-width:2px
```

### Apps Module Architecture

The `apps` module focuses on providing tools and utilities for analyzing application bundles, specifically targeting Next.js applications.

```mermaid
flowchart LR
    subgraph Apps
        A[bundle-analyzer] -- Bundle analysis tools --> B(lib)
        A --> C(components)
    end
    style Apps fill:#f9f,stroke:#333,stroke-width:2px
```

### Rspack Module Architecture

The `rspack` module integrates Rspack with Next.js, focusing on handling external dependencies.

```mermaid
flowchart LR
    subgraph Rspack
        A[rspack] -- Rspack integration --> B(lib)
    end
    style Rspack fill:#f9f,stroke:#333,stroke-width:2px
```

### Scripts Module Architecture

The `scripts` module appears to be focused on handling command-line interface options for a "pack-next" utility.

```mermaid
flowchart LR
    subgraph Scripts
        A[pack-next] -- Pack Next.js application --> B(CliOptions)
    end
    style Scripts fill:#f9f,stroke:#333,stroke-width:2px
```

## Core Modules Documentation

- [Packages](packages_next.md)
- [Turbo](turbopack.md)
- [Apps](apps.md)
- [Rspack](rspack.md)
- [Scripts](scripts.md)